# Routing

## Purpose

Define how HTTP routes are organized under `app/api/`, how they are mounted with `/api/v1`, and why `main.py` stays thin.

## Status

Draft (reflects current implementation)

## Scope

- Existing: `app/api/router.py` aggregates routers (health, projects, agents, tasks, sessions, inbox, scheduler, goals, skills, templates, triggers, automations, agentos); `main.py` includes `api_router` with `prefix="/api/v1"` and keeps unversioned `/` and `/health`. Agent grants: `GET/PUT /agents/{id}/grants` and `/agentos/agents/{name}/grants`. Network policy: `GET/PUT /agents/{id}/network` and `/agentos/agents/{name}/network`. Filesystem ACL: `GET/PUT /agents/{id}/fs` and `/agentos/agents/{name}/fs`. Secret refs: `GET/PUT /agents/{id}/secrets` and `/agentos/agents/{name}/secrets` (names/keys only).
- Active: Phase 5 webhook + `POST /api/v1/triggers/lead-status-nuevo` + `GET/POST/PATCH/DELETE /api/v1/automations` and `POST /api/v1/automations/tick` (optional `now` test clock). — [ROADMAP.md](../ROADMAP.md).
- Future: additional API versions if breaking changes require them; single-operator auth-protected routers.

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
| `GET /api/v1/demo-error` | `api/routes/health.py` | Learning demo (`NotFoundError`); remove later |

## Conventions

- One router module per area under `app/api/routes/`.
- Register new routers in `app/api/router.py`.
- Keep business logic out of route handlers (prefer `services/` / `agentos/`).
- Raise `AppError` subclasses instead of ad-hoc error JSON ([error-handling.md](error-handling.md)).

## Code

- [`backend/app/api/router.py`](../../backend/app/api/router.py)
- [`backend/app/api/routes/health.py`](../../backend/app/api/routes/health.py)
- [`backend/app/main.py`](../../backend/app/main.py)

## TODO

- Remove `demo-error` when no longer needed for learning.
- Document auth-protected routers when single-operator auth lands (Future — not old “Fase 4”).
- Keep OpenAPI and [CONTRACT.md](../agentos/CONTRACT.md) aligned with mounted routes.
