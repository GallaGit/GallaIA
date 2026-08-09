# Backend Architecture

## Purpose

Describe the backend’s layered package layout, what is active today, and how documentation under `docs/backend/` deep-dives into each concern.

## Status

Draft

## Scope

- Existing (active code):
  - `app/main.py` — FastAPI app, lifespan, middleware, exception handlers, `/`, `/health`, mounts `/api/v1`
  - `app/core/config.py` — `Settings` / `get_settings()`
  - `app/core/logging.py` — `setup_logging` / `get_logger`
  - `app/api/router.py` — aggregates v1 routers
  - `app/api/routes/health.py` — `GET /api/v1/health` (+ demo-error)
  - `app/api/dependencies/settings.py` — `SettingsDep`
  - `app/exceptions/` — `AppError` + handlers
  - `app/middleware/request_id.py` — `X-Request-ID` + request logging
  - `Dockerfile`, `docker-compose.yml`, `.env.example`
- Existing (reserved scaffold only): `db/`, `models/`, `schemas/`, `repositories/`, `services/`, `providers/`, `agents/`, `tools/`, `memory/`, `rag/`, `utils/`, `core/security.py`
- Planned: DB/auth/chat layers (Fase 3+).
- Future: activate reserved AI packages per roadmap.

## Package roles

| Package | Role | State |
|---------|------|-------|
| `api/` | HTTP routes, router, dependencies | Active |
| `core/` | Config, logging, security helpers | Config + logging active |
| `exceptions/` | App errors + HTTP handlers | Active |
| `middleware/` | Cross-cutting HTTP middleware | Active (request-id) |
| `db/` | Engine/session and migrations | Scaffold (Fase 3+) |
| `models/` | ORM models | Scaffold |
| `schemas/` | Pydantic API schemas | Scaffold |
| `repositories/` | Data access | Scaffold |
| `services/` | Use-case orchestration | Scaffold |
| `providers/` | External AI provider adapters | Scaffold |
| `agents/`, `tools/`, `memory/`, `rag/` | Later seasons | Reserved |
| `utils/` | Helpers | Scaffold |

## Deep-dives

See [docs/backend/](../backend/).

## TODO

- Mark packages Active vs Reserved as phases progress.
- Do not reorganize into feature-based or hexagonal layouts ([ADR-002](../adr/ADR-002-project-structure.md)).
