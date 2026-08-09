from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración central de la aplicación."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "GallaAI API"
    app_env: str = "development"
    app_debug: bool = True
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://gallaai:gallaai@localhost:5432/gallaai"


@lru_cache
def get_settings() -> Settings:
    """Devuelve Settings en cache (una instancia por proceso)."""
    return Settings()
