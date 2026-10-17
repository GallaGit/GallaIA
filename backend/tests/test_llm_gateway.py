"""F2.1a — LLM gateway chain: OpenRouter -> Groq -> mock (fake transport, no network)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.llm import gateway
from app.llm.gateway import LLMError, ProviderConfig
from app.services.thread_agents import default_llm, mock_llm

OPENROUTER_CFG = ProviderConfig(
    name="openrouter",
    api_key="or-test-key",
    model="test/or-model",
    base_url="https://openrouter.ai/api/v1",
)
GROQ_CFG = ProviderConfig(
    name="groq",
    api_key="gq-test-key",
    model="llama-3.3-70b-versatile",
    base_url="https://api.groq.com/openai/v1",
)

SYSTEM = "You are orquestador \u2014 GallaIA."
USER = "Construye la feature X"


def _reply(text):
    return {"choices": [{"message": {"role": "assistant", "content": text}}]}


def _transport(handlers):
    """Fake transport. `handlers` maps provider name -> dict | Exception | callable."""
    calls: list[dict] = []

    def _send(url, headers, payload, timeout):
        calls.append(
            {
                "url": url,
                "headers": dict(headers),
                "payload": payload,
                "timeout": timeout,
            }
        )
        name = "openrouter" if "openrouter" in url else "groq"
        handler = handlers[name]
        if isinstance(handler, Exception):
            raise handler
        return handler() if callable(handler) else handler

    return _send, calls


def _no_keys(monkeypatch):
    """Clear both provider keys from env and the cached Settings."""
    for var in ("OPENROUTER_API_KEY", "OPENROUTER_MODEL", "OPENROUTER_BASE_URL"):
        monkeypatch.delenv(var, raising=False)
    for var in ("GROQ_API_KEY", "GROQ_MODEL", "GROQ_BASE_URL"):
        monkeypatch.delenv(var, raising=False)
    get_settings.cache_clear()


def test_no_providers_uses_mock():
    _send, calls = _transport({})

    result = gateway.complete(SYSTEM, USER, providers=[], transport=_send)

    assert result.provider == "mock"
    assert result.model == "mock"
    assert result.text == mock_llm(SYSTEM, USER)
    assert calls == []


def test_openrouter_success_does_not_call_groq():
    _send, calls = _transport(
        {"openrouter": _reply("respuesta openrouter"), "groq": _reply("respuesta groq")}
    )

    result = gateway.complete(
        SYSTEM, USER, providers=[OPENROUTER_CFG, GROQ_CFG], transport=_send
    )

    assert result.provider == "openrouter"
    assert result.model == "openrouter/test/or-model"
    assert result.text == "respuesta openrouter"
    assert len(calls) == 1
    call = calls[0]
    assert call["url"].endswith("/chat/completions")
    assert call["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert call["headers"]["Authorization"] == "Bearer or-test-key"
    assert call["headers"]["Content-Type"] == "application/json"
    assert call["payload"]["model"] == "test/or-model"
    assert call["payload"]["messages"] == [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": USER},
    ]


def test_openrouter_failure_falls_back_to_groq():
    _send, calls = _transport(
        {
            "openrouter": LLMError("HTTP 429: slow down"),
            "groq": _reply("respuesta groq"),
        }
    )

    result = gateway.complete(
        SYSTEM, USER, providers=[OPENROUTER_CFG, GROQ_CFG], transport=_send
    )

    assert result.provider == "groq"
    assert result.model == "groq/llama-3.3-70b-versatile"
    assert result.text == "respuesta groq"
    assert len(calls) == 2
    assert calls[1]["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert calls[1]["headers"]["Authorization"] == "Bearer gq-test-key"
    assert "HTTP-Referer" not in calls[1]["headers"]


def test_all_providers_fail_returns_mock():
    _send, calls = _transport(
        {
            "openrouter": LLMError("boom"),
            "groq": LLMError("HTTP 500: boom"),
        }
    )

    result = gateway.complete(
        SYSTEM, USER, providers=[OPENROUTER_CFG, GROQ_CFG], transport=_send
    )

    assert result.provider == "mock"
    assert result.model == "mock"
    assert result.text == mock_llm(SYSTEM, USER)
    assert len(calls) == 2


def test_empty_choices_on_openrouter_falls_back_to_groq():
    _send, calls = _transport(
        {"openrouter": {"choices": []}, "groq": _reply("respuesta groq")}
    )

    result = gateway.complete(
        SYSTEM, USER, providers=[OPENROUTER_CFG, GROQ_CFG], transport=_send
    )

    assert result.provider == "groq"
    assert result.text == "respuesta groq"
    assert len(calls) == 2


def test_list_of_parts_content_is_joined():
    def _parts():
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": [
                            {"type": "text", "text": "parte 1 "},
                            "parte 2",
                            {"type": "text", "text": "parte 3"},
                        ],
                    }
                }
            ]
        }

    _send, _calls = _transport({"openrouter": _parts})

    result = gateway.complete(SYSTEM, USER, providers=[OPENROUTER_CFG], transport=_send)

    assert result.text == "parte 1 parte 2parte 3"
    assert result.provider == "openrouter"


def test_configured_providers_only_groq_when_only_groq_key_set(monkeypatch):
    _no_keys(monkeypatch)
    try:
        assert gateway.configured_providers() == []

        monkeypatch.setenv("GROQ_API_KEY", "gq-from-env")
        get_settings.cache_clear()

        providers = gateway.configured_providers()

        assert [p.name for p in providers] == ["groq"]
        assert providers[0].api_key == "gq-from-env"
        assert providers[0].base_url == "https://api.groq.com/openai/v1"
    finally:
        get_settings.cache_clear()


def test_default_llm_returns_mock_without_keys(monkeypatch):
    _no_keys(monkeypatch)
    try:
        assert default_llm() is mock_llm
    finally:
        get_settings.cache_clear()
