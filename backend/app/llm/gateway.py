"""F2.1 — LLM gateway: OpenRouter -> Groq -> deterministic mock.

Single entry point `complete(system, user, model=...)` for thread agents and the
AgentOS session runners. Providers are tried in order; the first one that
answers wins. Model names are LiteLLM-style ("openrouter/<model>",
"groq/<model>", "mock").

F2.1b adds:
- per-agent model selection (`resolve_model` / `providers_for_model`);
- one `UsageRecord` per attempt (provider, model, tokens, latency, cost when
  trivial) handed to an optional `on_usage` sink and logged;
- an optional `litellm` backend (GALLAIA_LLM_BACKEND=litellm). `litellm` is NOT
  a required dependency: when it is not installed the plain HTTP backend is used.

Never log or echo API keys.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, replace
from typing import Callable

from app.providers import openrouter as openrouter_provider

logger = logging.getLogger("app.llm.usage")

OPENROUTER = "openrouter"
GROQ = "groq"
MOCK = "mock"

BACKEND_HTTP = "http"
BACKEND_LITELLM = "litellm"

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Agent.model values that mean "use the configured default".
_INHERIT_VALUES = frozenset({"", "inherit", "default"})


class LLMError(Exception):
    """Transport, HTTP or payload failure. Never carries credentials."""


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    api_key: str
    model: str
    base_url: str


@dataclass(frozen=True)
class UsageRecord:
    """One provider attempt (or the mock fallback). No prompts, no keys."""

    provider: str
    model: str
    ok: bool
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    backend: str = BACKEND_HTTP
    error: str | None = None


@dataclass(frozen=True)
class LLMResult:
    text: str
    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    cost_usd: float | None = None
    # Every attempt of this call, in order (failed providers + the winner).
    attempts: tuple[UsageRecord, ...] = field(default_factory=tuple)


Transport = Callable[[str, dict, dict, float], dict]
UsageSink = Callable[[UsageRecord], None]


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


def llm_backend() -> str:
    """`http` (default) or `litellm` (GALLAIA_LLM_BACKEND)."""
    value = (
        _setting("llm_backend") or os.getenv("GALLAIA_LLM_BACKEND") or BACKEND_HTTP
    ).strip().lower()
    return BACKEND_LITELLM if value == BACKEND_LITELLM else BACKEND_HTTP


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


# ---------------------------------------------------------------------------
# Per-agent model selection
# ---------------------------------------------------------------------------


def is_legacy_model(model: str) -> bool:
    """Old Anthropic defaults (e.g. `claude-sonnet-4`) stored before F2.1b.

    They are not valid OpenRouter ids, so they map to the configured default
    instead of failing; existing rows keep working without a data migration.
    """
    low = (model or "").strip().lower()
    return "/" not in low and low.startswith("claude")


def resolve_model(model: str | None) -> tuple[str | None, str | None]:
    """Map an Agent.model value to `(provider, model_id)`.

    - empty / inherit / legacy `claude-*` -> `(None, None)` (configured defaults)
    - `mock` -> `("mock", None)`
    - `groq/<id>` -> `("groq", "<id>")`
    - `openrouter/<id>` or any other id (OpenRouter style `vendor/model[:free]`)
      -> `("openrouter", "<id>")`
    """
    value = (model or "").strip()
    if value.lower() in _INHERIT_VALUES or is_legacy_model(value):
        return None, None
    if value.lower() == MOCK:
        return MOCK, None
    prefix, sep, rest = value.partition("/")
    if sep and prefix.lower() == GROQ and rest:
        return GROQ, rest
    if sep and prefix.lower() == OPENROUTER and rest:
        return OPENROUTER, rest
    return OPENROUTER, value


def providers_for_model(
    model: str | None, providers: list[ProviderConfig]
) -> list[ProviderConfig]:
    """Apply an agent's model to the provider chain.

    OpenRouter ids override the OpenRouter model (Groq keeps its own default as
    fallback). `groq/<id>` overrides Groq's model and tries Groq first.
    `mock` skips every provider.
    """
    provider, model_id = resolve_model(model)
    if provider is None:
        return list(providers)
    if provider == MOCK:
        return []
    out = [replace(p, model=model_id) if p.name == provider else p for p in providers]
    if provider == GROQ:
        out.sort(key=lambda p: 0 if p.name == GROQ else 1)
    return out


# ---------------------------------------------------------------------------
# Transports / backends
# ---------------------------------------------------------------------------


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


def _extra_headers(provider: ProviderConfig) -> dict:
    if provider.name == OPENROUTER:
        return {"HTTP-Referer": "http://localhost:5173", "X-Title": "GallaAI AgentOS"}
    return {}


def _litellm_module():
    """Import litellm lazily; None when it is not installed."""
    try:
        import litellm  # type: ignore[import-not-found]
    except Exception:  # noqa: BLE001 — optional dependency
        return None
    return litellm


def _as_dict(response) -> dict:
    if isinstance(response, dict):
        return response
    for attr in ("model_dump", "dict", "to_dict"):
        fn = getattr(response, attr, None)
        if callable(fn):
            try:
                data = fn()
            except Exception:  # noqa: BLE001
                continue
            if isinstance(data, dict):
                return data
    try:
        return json.loads(json.dumps(response, default=lambda o: o.__dict__))
    except Exception as exc:  # noqa: BLE001
        raise LLMError("unexpected litellm response payload") from exc


def _litellm_send(litellm, provider: ProviderConfig, payload: dict, timeout: float) -> dict:
    try:
        response = litellm.completion(
            model=f"{provider.name}/{provider.model}",
            messages=payload["messages"],
            max_tokens=payload["max_tokens"],
            api_key=provider.api_key,
            api_base=provider.base_url,
            timeout=timeout,
            extra_headers=_extra_headers(provider) or None,
        )
    except Exception as exc:  # noqa: BLE001 — never surface the key
        msg = str(exc).replace(provider.api_key, "***") if provider.api_key else str(exc)
        raise LLMError(f"litellm: {msg[:500]}") from exc
    return _as_dict(response)


def _int_or_none(value) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _usage_tokens(data: dict) -> tuple[int | None, int | None]:
    usage = data.get("usage")
    if not isinstance(usage, dict):
        return None, None
    return _int_or_none(usage.get("prompt_tokens")), _int_or_none(
        usage.get("completion_tokens")
    )


def estimate_cost(provider: str, model_id: str) -> float | None:
    """Only the trivial cases: mock and OpenRouter `:free` models cost 0."""
    if provider == MOCK:
        return 0.0
    if provider == OPENROUTER and model_id.endswith(":free"):
        return 0.0
    return None


def call_provider(
    provider: ProviderConfig,
    system: str,
    user: str,
    *,
    max_tokens: int = 512,
    timeout: float = 90.0,
    transport: Transport | None = None,
    backend: str | None = None,
) -> LLMResult:
    """Call one OpenAI-compatible /chat/completions endpoint (or litellm)."""
    payload = {
        "model": provider.model,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    started = time.perf_counter()
    litellm = None
    if transport is None and (backend or llm_backend()) == BACKEND_LITELLM:
        litellm = _litellm_module()
        if litellm is None:
            logger.warning(
                "GALLAIA_LLM_BACKEND=litellm but litellm is not installed; using http"
            )
    if litellm is not None:
        data = _litellm_send(litellm, provider, payload, timeout)
    else:
        send = transport or _urllib_transport
        url = f"{provider.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {provider.api_key}",
            "Content-Type": "application/json",
            **_extra_headers(provider),
        }
        data = send(url, headers, payload, timeout)
    latency_ms = int((time.perf_counter() - started) * 1000)

    choices = data.get("choices") or []
    if not choices:
        raise LLMError(f"empty choices in {provider.name} response")
    first = choices[0] if isinstance(choices[0], dict) else {}
    text = _message_text(first.get("message") or {})
    if not text:
        raise LLMError(f"empty text in {provider.name} response")
    input_tokens, output_tokens = _usage_tokens(data)
    return LLMResult(
        text=text,
        provider=provider.name,
        model=f"{provider.name}/{provider.model}",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        cost_usd=estimate_cost(provider.name, provider.model),
    )


def _emit(record: UsageRecord, on_usage: UsageSink | None) -> None:
    logger.info(
        "llm.call provider=%s model=%s ok=%s backend=%s in=%s out=%s latency_ms=%s",
        record.provider,
        record.model,
        record.ok,
        record.backend,
        record.input_tokens,
        record.output_tokens,
        record.latency_ms,
    )
    if on_usage is None:
        return
    try:
        on_usage(record)
    except Exception:  # noqa: BLE001 — usage logging must never break a call
        logger.exception("llm usage sink failed")


def _redact(message: str, providers: list[ProviderConfig]) -> str:
    for p in providers:
        if p.api_key:
            message = message.replace(p.api_key, "***")
    return message[:300]


def complete(
    system: str,
    user: str,
    *,
    model: str | None = None,
    providers: list[ProviderConfig] | None = None,
    transport: Transport | None = None,
    fallback: Callable[[str, str], str] | None = None,
    max_tokens: int = 512,
    timeout: float = 90.0,
    on_usage: UsageSink | None = None,
) -> LLMResult:
    """Try each provider in order; fall back to the offline mock generator.

    `model` is the agent's model (see `resolve_model`); None keeps defaults.
    `on_usage` receives one `UsageRecord` per attempt.
    """
    if providers is None:
        providers = configured_providers()
    chain = providers_for_model(model, providers)
    backend = BACKEND_HTTP if transport is not None else llm_backend()
    attempts: list[UsageRecord] = []

    for provider in chain:
        started = time.perf_counter()
        try:
            result = call_provider(
                provider,
                system,
                user,
                max_tokens=max_tokens,
                timeout=timeout,
                transport=transport,
                backend=backend,
            )
        except LLMError as exc:  # network/HTTP/empty failure -> next provider
            record = UsageRecord(
                provider=provider.name,
                model=f"{provider.name}/{provider.model}",
                ok=False,
                latency_ms=int((time.perf_counter() - started) * 1000),
                backend=backend,
                error=_redact(str(exc), chain),
            )
            attempts.append(record)
            _emit(record, on_usage)
            continue
        record = UsageRecord(
            provider=result.provider,
            model=result.model,
            ok=True,
            latency_ms=result.latency_ms or 0,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cost_usd=result.cost_usd,
            backend=backend,
        )
        attempts.append(record)
        _emit(record, on_usage)
        return replace(result, attempts=tuple(attempts))

    if fallback is None:
        from app.services.thread_agents import mock_llm

        fallback = mock_llm
    started = time.perf_counter()
    text = fallback(system, user)
    record = UsageRecord(
        provider=MOCK,
        model=MOCK,
        ok=True,
        latency_ms=int((time.perf_counter() - started) * 1000),
        cost_usd=0.0,
        backend=MOCK,
    )
    attempts.append(record)
    _emit(record, on_usage)
    return LLMResult(
        text=text,
        provider=MOCK,
        model=MOCK,
        latency_ms=record.latency_ms,
        cost_usd=0.0,
        attempts=tuple(attempts),
    )
