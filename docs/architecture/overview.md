# Architecture Overview

## Purpose

Provide a single map of GallaAI’s system shape: how frontend, backend, data, and runners relate, and why the project stays on a simple layered architecture.

## Status

Draft

## Scope

- Existing: Repository layout (`backend/`, `frontend/`, `docs/`); FastAPI with Settings, logging, health, Docker Compose (UI+API), `/api/v1`, AgentOS control plane (projects/agents/tasks/sessions/inbox + `/api/v1/agentos`), SQLite, React+Vite atelier UI, mock/stub runners.
- Planned: AgentOS Phase 2+ (Isolation, Templates, Goals, Triggers) per [ROADMAP.md](../ROADMAP.md) — **documentation first**, not implemented in the Phase 1 MVP.
- Future: Postgres when SQLite is not enough ([ADR-003](../adr/ADR-003-postgresql.md)), single-operator auth, RAG, product chat, PWA.

## Current runtime shape

```text
Browser (React + Vite atelier)
    → FastAPI (backend)
        → RequestIdMiddleware / AppError handlers
        → GET /health, GET /api/v1/health
        → /api/v1/{projects,agents,tasks,sessions,inbox}  (SQLite)
        → /api/v1/agentos/*                               (in-memory package)
        → mock runner | Anthropic Messages stub
```

Product map: [product/AGENTOS.md](../product/AGENTOS.md). Module boundaries: [product/MODULE_BOUNDARIES.md](../product/MODULE_BOUNDARIES.md).

## Architectural stance

- Layered architecture under `backend/app/` ([ADR-002](../adr/ADR-002-project-structure.md)).
- Not hexagonal, not CQRS, not DDD, not feature-based packages.
- Educational clarity over premature abstraction.
- AgentOS Phase numbering is canonical; do not treat “Fase 3” as Postgres/chat.

## Related docs

- [backend.md](backend.md) · [frontend.md](frontend.md) · [api.md](api.md) · [database.md](database.md)
- [ROADMAP.md](../ROADMAP.md) · [CONTROL_PLANE_NAV.md](../product/CONTROL_PLANE_NAV.md)

## TODO

- Add a diagram under `docs/assets/diagrams/` when useful.
- Keep Existing vs Planned vs Future explicit in every update.
