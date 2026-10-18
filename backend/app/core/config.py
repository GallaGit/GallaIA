from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Default agent model: OpenRouter primary provider.
DEFAULT_OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"


class Settings(BaseSettings):
    """Configuracion central de la aplicacion."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "GallaAI AgentOS"
    app_env: str = "development"
    app_debug: bool = True
    log_level: str = "INFO"
    # MVP: SQLite. Postgres later: postgresql+psycopg://gallaai:gallaai@localhost:5432/gallaai
    database_url: str = "sqlite:///./data/gallaia.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # GALLAIA-SEC-011: Host header allow-list (DNS rebinding). "testserver" = TestClient.
    allowed_hosts: str = "localhost,127.0.0.1,testserver"
    # GALLAIA-SEC-007: extra origins for the SPA CSP connect-src (comma-separated).
    # Only needed if the UI is built with VITE_API_URL pointing to another origin.
    csp_extra_connect_src: str = ""
    # Optional AgentOS LLM — empty keys mean mock runner only. Never hardcode secrets.
    # LEGACY: Anthropic only for the in-memory AgentOS runner when explicitly
    # requested; the control-plane runner uses the gateway. Provider chain:
    # OpenRouter (primary) -> Groq (fallback) -> deterministic mock.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"
    openrouter_api_key: str = ""
    openrouter_model: str = DEFAULT_OPENROUTER_MODEL
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # Groq: OpenAI-compatible endpoint used as fallback provider.
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    # F2.1b: gateway backend. "http" (default, urllib) | "litellm" (optional,
    # only if the `litellm` package is installed; otherwise falls back to http).
    llm_backend: str = Field(
        default="http",
        validation_alias=AliasChoices("GALLAIA_LLM_BACKEND", "LLM_BACKEND", "llm_backend"),
    )
    # Phase 5 Triggers: shared secret for public webhook (empty = deny all).
    gallaia_webhook_secret: str = ""
    # Phase 7: mock (in-process) | local (future OS binary -> local-stub for now).
    runner_route: str = Field(
        default="mock",
        validation_alias=AliasChoices(
            "GALLAIA_RUNNER_ROUTE",
            "RUNNER_ROUTE",
            "runner_route",
        ),
    )
    # Phase 7: optional Web Push VAPID (empty = push endpoints return 503). Never commit real keys.
    vapid_public_key: str = Field(
        default="",
        validation_alias=AliasChoices("VAPID_PUBLIC_KEY", "vapid_public_key"),
    )
    vapid_private_key: str = Field(
        default="",
        validation_alias=AliasChoices("VAPID_PRIVATE_KEY", "vapid_private_key"),
    )

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        # GALLAIA-SEC-004: credentials are enabled, so wildcards are not allowed.
        if any("*" in o for o in origins):
            raise ValueError("CORS_ORIGINS must list explicit origins; '*' is not allowed")
        return origins

    @property
    def csp_extra_connect_src_list(self) -> list[str]:
        return [o.strip() for o in self.csp_extra_connect_src.split(",") if o.strip()]

    @property
    def allowed_host_list(self) -> list[str]:
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]


@lru_cache
def get_settings() -> Settings:
    """Devuelve Settings en cache (una instancia por proceso)."""
    return Settings()
