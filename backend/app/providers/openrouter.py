"""OpenRouter Chat Completions adapter for AgentOS runners.

Used when OPENROUTER_API_KEY is set. Never hardcode secrets.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass


class OpenRouterError(Exception):
    """OpenRouter HTTP or payload failure."""


@dataclass(frozen=True)
class OpenRouterCompletion:
    text: str
    model: str


def _settings():
    try:
        from app.core.config import get_settings

        return get_settings()
    except Exception:  # noqa: BLE001 — settings may be unavailable in isolation
        return None


def openrouter_api_key() -> str:
    settings = _settings()
    if settings is not None:
        key = (settings.openrouter_api_key or "").strip()
        if key:
            return key
    return (os.getenv("OPENROUTER_API_KEY") or "").strip()


def openrouter_model() -> str:
    settings = _settings()
    if settings is not None:
        model = (settings.openrouter_model or "").strip()
        if model:
            return model
    return (
        os.getenv("OPENROUTER_MODEL") or "nvidia/nemotron-3-ultra-550b-a55b:free"
    ).strip()


def openrouter_base_url() -> str:
    settings = _settings()
    if settings is not None:
        base = (settings.openrouter_base_url or "").strip()
        if base:
            return base.rstrip("/")
    return (
        os.getenv("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1"
    ).rstrip("/")


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


def complete(*, system: str, user: str, max_tokens: int = 512, timeout: float = 90.0) -> OpenRouterCompletion:
    api_key = openrouter_api_key()
    if not api_key:
        raise OpenRouterError("OPENROUTER_API_KEY is not set")

    model = openrouter_model()
    url = f"{openrouter_base_url()}/chat/completions"
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "GallaAI AgentOS",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:500]
        raise OpenRouterError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise OpenRouterError(str(exc.reason or exc)) from exc

    choices = data.get("choices") or []
    if not choices:
        raise OpenRouterError("empty choices in OpenRouter response")
    text = _message_text(choices[0].get("message") or {})
    return OpenRouterCompletion(text=text or "(empty OpenRouter response)", model=model)
