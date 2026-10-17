"""LLM gateway (F2.1a): OpenRouter -> Groq -> mock, provider agnostic."""

from app.llm.gateway import (
    GROQ,
    MOCK,
    OPENROUTER,
    LLMError,
    LLMResult,
    ProviderConfig,
    Transport,
    call_provider,
    complete,
    configured_providers,
    groq_api_key,
    groq_base_url,
    groq_model,
)

__all__ = [
    "GROQ",
    "MOCK",
    "OPENROUTER",
    "LLMError",
    "LLMResult",
    "ProviderConfig",
    "Transport",
    "call_provider",
    "complete",
    "configured_providers",
    "groq_api_key",
    "groq_base_url",
    "groq_model",
]
