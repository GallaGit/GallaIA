"""F2.1a — LLM gateway: OpenRouter -> Groq -> deterministic mock.

Single entry point `complete(system, user)` for thread agents. Providers are
tried in order; the first one that answers wins. Model names are LiteLLM-style
("openrouter/<model>", "groq/<model>", "mock") so a later LiteLLM backend can be
swapped in without touching callers. Never log or echo API keys.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable

from app.providers import openrouter as openrouter_provider

OPENROUTER = "openrouter"
GROQ = "groq"
MOCK = "mock"

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class LLMError(Exception):
    """Transport, HTTP or payload failure. Never carries credentials."""


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    api_key: str
    model: str
    base_url: str


@dataclass(frozen=True)
class LLMResult:
    text: str
    provider: str
    model: str


Transport = Callable[[str, dict, dict, float], dict]


def _settings():
    try:
        from app.core.config import get_settings

        return get_settings()
    except Exception:  # noqa: BLE001 — settings may be unavailable in isolation
        return None


def _setting(name: str) -> str:
    settings = _settings()
    if settings is not None:
        value = (getattr(settings, name, "") or "").strip()
        if value:
            return value
    return ""


def groq_api_key() -> str:
    return _setting("groq_api_key") or (os.getenv("GROQ_API_KEY") or "").strip()


def groq_model() -> str:
    return _setting("groq_model") or (
        os.getenv("GROQ_MODEL") or DEFAULT_GROQ_MODEL
    ).strip()


def groq_base_url() -> str:
    return (
        _setting("groq_base_url") or os.getenv("GROQ_BASE_URL") or DEFAULT_GROQ_BASE_URL
    ).rstrip("/")


def configured_providers() -> list[ProviderConfig]:
    """OpenRouter first, then Groq. Only providers with a non-empty key."""
    providers: list[ProviderConfig] = []
    openrouter_key = openrouter_provider.openrouter_api_key()
    if openrouter_key:
        providers.append(
            ProviderConfig(
                name=OPENROUTER,
                api_key=openrouter_key,
                model=openrouter_provider.openrouter_model(),
                base_url=openrouter_provider.openrouter_base_url(),
            )
        )
    groq_key = groq_api_key()
    if groq_key:
        providers.append(
            ProviderConfig(
                name=GROQ,
                api_key=groq_key,
                model=groq_model(),
                base_url=groq_base_url(),
            )
        )
    return providers


def _message_text(message: dict) -> str:
    content = message.get("content")
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                parts.append(str(part.get("text") or ""))
        return "".join(parts).strip()
    if isinstance(content, str):
        return content.strip()
    return ""


def _urllib_transport(url: str, headers: dict, payload: dict, timeout: float) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers=dict(headers),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:500]
        raise LLMError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise LLMError(str(exc.reason or exc)) from exc
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise LLMError("invalid JSON in provider response") from exc
    if not isinstance(data, dict):
        raise LLMError("unexpected provider response payload")
    return data


def call_provider(
    provider: ProviderConfig,
    system: str,
    user: str,
    *,
    max_tokens: int = 512,
    timeout: float = 90.0,
    transport: Transport | None = None,
) -> LLMResult:
    """Call one OpenAI-compatible /chat/completions endpoint."""
    send = transport or _urllib_transport
    url = f"{provider.base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": provider.model,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
    }
    if provider.name == OPENROUTER:
        headers["HTTP-Referer"] = "http://localhost:5173"
        headers["X-Title"] = "GallaAI AgentOS"

    data = send(url, headers, payload, timeout)
    choices = data.get("choices") or []
    if not choices:
        raise LLMError(f"empty choices in {provider.name} response")
    text = _message_text(choices[0].get("message") or {})
    if not text:
        raise LLMError(f"empty text in {provider.name} response")
    return LLMResult(text=text, provider=provider.name, model=f"{provider.name}/{provider.model}")


def complete(
    system: str,
    user: str,
    *,
    providers: list[ProviderConfig] | None = None,
    transport: Transport | None = None,
    fallback: Callable[[str, str], str] | None = None,
    max_tokens: int = 512,
    timeout: float = 90.0,
) -> LLMResult:
    """Try each provider in order; fall back to the offline mock generator."""
    if providers is None:
        providers = configured_providers()

    for provider in providers:
        try:
            return call_provider(
                provider,
                system,
                user,
                max_tokens=max_tokens,
                timeout=timeout,
                transport=transport,
            )
        except LLMError:
            continue  # network/HTTP/empty failure -> next provider

    if fallback is None:
        from app.services.thread_agents import mock_llm

        fallback = mock_llm
    return LLMResult(text=fallback(system, user), provider=MOCK, model=MOCK)
