from functools import lru_cache

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
    # Optional AgentOS LLM — empty means mock runner only. Never hardcode secrets.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Devuelve Settings en cache (una instancia por proceso)."""
    return Settings()
