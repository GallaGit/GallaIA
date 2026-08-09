# Architecture Overview

## Purpose

Provide a single map of GallaAI’s system shape: how frontend, backend, data, and AI providers relate over time, and why the project stays on a simple layered architecture.

## Status

Draft

## Scope

- Existing: Repository layout (`backend/`, `frontend/`, `docs/`); runnable FastAPI API with Settings, logging, health endpoints, Docker Compose, and `/api/v1` router prefix.
- Planned: Finish Fase 2 (global errors, middleware, shared dependencies); then DB, auth, users, and chat per [ROADMAP.md](../ROADMAP.md).
- Future: Persistence product features, RAG, agents, automations, and dashboard in later seasons.

## Current runtime shape

```text
Client / browser
    → FastAPI (backend)
        → GET /health          (infra)
        → GET /api/v1/health   (versioned API)
```

Frontend and AI providers are not wired yet.

## Architectural stance

- Layered architecture under `backend/app/` ([ADR-002](../adr/ADR-002-project-structure.md)).
- Not hexagonal, not CQRS, not DDD, not feature-based packages.
- Educational clarity over premature abstraction.

## Related docs

- [backend.md](backend.md) · [frontend.md](frontend.md) · [api.md](api.md) · [database.md](database.md)

## TODO

- Add a diagram under `docs/assets/diagrams/` when useful.
- Keep Existing vs Planned vs Future explicit in every update.
