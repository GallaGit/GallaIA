# Backend Architecture

## Purpose

Describe the backend’s layered package layout, what is active today, and how documentation under `docs/backend/` deep-dives into each concern.

## Status

Draft

## Scope

- Existing (active code):
  - `app/main.py` — FastAPI app, lifespan, middleware, exception handlers, `/`, `/health`, mounts `/api/v1`, static UI when built
  - `app/core/config.py` — `Settings` / `get_settings()` (optional OpenRouter + Anthropic)
  - `app/providers/openrouter.py` — OpenRouter Chat Completions adapter
  - `app/core/logging.py` — `setup_logging` / `get_logger`
  - `app/api/router.py` — aggregates v1 routers (health, projects, agents, tasks, sessions, inbox, agentos)
  - `app/agentos/` — in-memory AgentOS package (seeds, runner, store, schemas)
  - `app/models`, `schemas`, `services`, routes under `api/routes/` — SQLAlchemy control plane + SQLite
  - `app/exceptions/`, `app/middleware/request_id.py`
  - Root `Dockerfile` + `docker-compose.yml`: UI + API in one container (see [docs/deployment/docker.md](../deployment/docker.md))
- Existing (reserved / light scaffold): `agents/`, `tools/`, `memory/`, `rag/`, `utils/`, `core/security.py`
- Planned: AgentOS Phase 2+ Isolation and beyond ([ROADMAP.md](../ROADMAP.md)) — doc first.
- Future: activate reserved AI packages (RAG, etc.) per roadmap; Postgres per [ADR-003](../adr/ADR-003-postgresql.md).

## Package roles

| Package | Role | State |
|---------|------|-------|
| `api/` | HTTP routes, router, dependencies | Active |
| `agentos/` | In-memory AgentOS MVP package | Active |
| `core/` | Config, logging, security helpers | Config + logging active |
| `exceptions/` | App errors + HTTP handlers | Active |
| `middleware/` | Cross-cutting HTTP middleware | Active (request-id) |
| `db/` | Engine/session and migrations | Active for SQLite control plane (Alembic/Postgres later) |
| `models/` | ORM models | Active (control plane) |
| `schemas/` | Pydantic API schemas | Active |
| `repositories/` | Data access | As used by control plane |
| `services/` | Use-case orchestration / prompts / runners | Active for AgentOS MVP |
| `providers/` | External AI provider adapters | Active: OpenRouter; Anthropic still inline in runners |
| `agents/`, `tools/`, `memory/`, `rag/` | Later seasons | Reserved |
| `utils/` | Helpers | Scaffold |

## Deep-dives

See [docs/backend/](../backend/). Product: [AGENTOS.md](../product/AGENTOS.md).

## TODO

- Mark packages Active vs Reserved as phases progress.
- Do not reorganize into feature-based or hexagonal layouts ([ADR-002](../adr/ADR-002-project-structure.md)).
