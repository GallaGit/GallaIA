# Routing

## Purpose

Define how HTTP routes are organized under `app/api/`, how they are mounted with `/api/v1`, and why `main.py` stays thin.

## Status

Draft (reflects current implementation)

## Scope

- Existing: `app/api/router.py` aggregates routers; `app/api/routes/health.py` exposes `GET /health` under the v1 prefix; `main.py` includes `api_router` with `prefix="/api/v1"` and keeps unversioned `/` and `/health`.
- Planned: more route modules (users, auth, chat); shared dependencies; consistent tags.
- Future: additional API versions if breaking changes require them.

## Mounting

```text
main.py
  include_router(api_router, prefix="/api/v1")
    → routes/health.py  GET /health
      → full path GET /api/v1/health
```

| Path | Module | Notes |
|------|--------|-------|
| `GET /` | `main.py` | Simple ping |
| `GET /health` | `main.py` | Infra health (compose/k8s-friendly) |
| `GET /api/v1/health` | `api/routes/health.py` | Versioned API health |

## Conventions

- One router module per area under `app/api/routes/`.
- Register new routers in `app/api/router.py`.
- Keep business logic out of route handlers (services later).

## Code

- [`backend/app/api/router.py`](../../backend/app/api/router.py)
- [`backend/app/api/routes/health.py`](../../backend/app/api/routes/health.py)
- [`backend/app/main.py`](../../backend/app/main.py)

## TODO

- Document auth-protected routers when Fase 4 starts.
- Link error-response conventions when global handlers land.
