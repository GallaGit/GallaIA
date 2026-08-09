# Dependency Injection

## Purpose

Explain why FastAPI `Depends` is used to wire shared resources into handlers, and what is injected today.

## Status

Draft (reflects current implementation)

## Scope

- Existing: `get_settings()` used as a dependency on health handlers (`Depends(get_settings)`); also called at import time in `main.py` for app title and logging setup.
- Planned: DB session dependency, auth/current-user dependency, shared API dependencies under `app/api/dependencies/`.
- Future: provider clients and other request-scoped resources.

## Pattern today

```python
from fastapi import Depends
from app.core.config import Settings, get_settings

def health(settings: Settings = Depends(get_settings)):
    ...
```

FastAPI calls `get_settings()`, caches via `@lru_cache`, and passes the `Settings` instance into the handler.

## Guidelines

- Prefer `Depends` for anything a route needs that is not pure request data.
- Keep dependency callables small and reusable.
- Do not hide business rules inside dependencies; orchestration belongs in services (when introduced).

## Code

- [`backend/app/core/config.py`](../../backend/app/core/config.py)
- [`backend/app/api/routes/health.py`](../../backend/app/api/routes/health.py)

## TODO

- Add `app/api/dependencies/` modules when DB/auth arrive.
- Document dependency lifetimes (request vs app scoped) with real examples.
