# Dependency Injection

## Purpose

Explain why FastAPI `Depends` is used to wire shared resources into handlers, and what is injected today.

## Status

Draft (reflects current implementation)

## Scope

- Existing: `SettingsDep` in `app/api/dependencies/settings.py` (`Annotated[Settings, Depends(get_settings)]`); used by health routes and infra `/health`. `get_settings()` is also called at import time in `main.py` for app title and logging setup.
- Planned: DB session dependency (`app/api/dependencies/db.py`), auth/current-user dependency.
- Future: provider clients and other request-scoped resources.

## Pattern today

```python
from app.api.dependencies.settings import SettingsDep

def api_health(settings: SettingsDep):
    ...
```

FastAPI resolves `Depends(get_settings)` from the annotation, caches via `@lru_cache`, and passes the `Settings` instance into the handler.

## Guidelines

- Prefer typed aliases under `app/api/dependencies/` over inline `Depends(...)` in every route.
- Keep dependency callables small and reusable.
- Do not hide business rules inside dependencies; orchestration belongs in services (when introduced).

## Code

- [`backend/app/api/dependencies/settings.py`](../../backend/app/api/dependencies/settings.py)
- [`backend/app/core/config.py`](../../backend/app/core/config.py)
- [`backend/app/api/routes/health.py`](../../backend/app/api/routes/health.py)

## TODO

- Add `db.py` / `auth.py` dependency modules in Fase 3–4.
- Document dependency lifetimes (request vs app scoped) with real examples.
