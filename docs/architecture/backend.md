# Backend Architecture

## Purpose

Describe the backend’s layered package layout, what is active today, and how documentation under `docs/backend/` deep-dives into each concern.

## Status

Draft

## Scope

- Existing (active code):
  - `app/main.py` — FastAPI app, lifespan, `/`, `/health`, mounts `/api/v1`
  - `app/core/config.py` — `Settings` / `get_settings()`
  - `app/core/logging.py` — `setup_logging` / `get_logger`
  - `app/api/router.py` — aggregates v1 routers
  - `app/api/routes/health.py` — `GET /api/v1/health`
  - `Dockerfile`, `docker-compose.yml`, `.env.example`
- Existing (reserved scaffold only): `db/`, `models/`, `schemas/`, `repositories/`, `services/`, `providers/`, `agents/`, `tools/`, `memory/`, `rag/`, `middleware/`, `exceptions/`, `utils/`, `core/security.py`
- Planned: global exception handlers, middleware, richer dependencies, then DB/auth/chat layers.
- Future: activate reserved AI packages per roadmap.

## Package roles

| Package | Role | State |
|---------|------|-------|
| `api/` | HTTP routes and router composition | Active (health) |
| `core/` | Config, logging, security helpers | Config + logging active |
| `db/` | Engine/session and migrations | Scaffold (Fase 3+) |
| `models/` | ORM models | Scaffold |
| `schemas/` | Pydantic API schemas | Scaffold |
| `repositories/` | Data access | Scaffold |
| `services/` | Use-case orchestration | Scaffold |
| `providers/` | External AI provider adapters | Scaffold |
| `agents/`, `tools/`, `memory/`, `rag/` | Later seasons | Reserved |
| `middleware/`, `exceptions/`, `utils/` | Cross-cutting support | Scaffold |

## Deep-dives

See [docs/backend/](../backend/).

## TODO

- Mark packages Active vs Reserved as phases progress.
- Do not reorganize into feature-based or hexagonal layouts ([ADR-002](../adr/ADR-002-project-structure.md)).
