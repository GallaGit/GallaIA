from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    # Optional AgentOS LLM — empty keys mean mock runner only. Never hardcode secrets.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"
    openrouter_api_key: str = ""
    openrouter_model: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
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
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Devuelve Settings en cache (una instancia por proceso)."""
    return Settings()
