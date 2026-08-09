from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings

# Alias tipado: se usa como tipo del parámetro en las rutas
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_settings_dependency() -> Settings:
    """Thin wrapper (útil si más adelante añades lógica extra)."""
    return get_settings()