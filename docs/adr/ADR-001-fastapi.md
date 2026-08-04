# ADR-001: Use FastAPI for the Backend HTTP API

## Status

Proposed (documentation: Draft)

## Context

GallaAI needs a Python HTTP API that will grow from a simple chat proxy into a larger AI platform. The project is educational: clarity, typing, and incremental delivery matter more than exotic architecture.

Candidates considered at a high level include FastAPI, Django, and Flask. The stack target in the product docs already names FastAPI.

## Decision

Use **FastAPI** as the backend web framework.

## Consequences

- Natural fit for Pydantic schemas, OpenAPI, and async I/O with AI provider clients.
- Dependency injection via `Depends` supports a thin-route / service-layer style.
- Team must learn FastAPI conventions (routers, lifespan, exception handlers).
- This ADR does **not** imply FastAPI is already configured in the repo; `backend/app/main.py` is still an empty scaffold.

## TODO

- Accept this ADR when the first runnable FastAPI app is introduced.
- Record rejected alternatives briefly if the team revisits the choice.
- Link to [docs/architecture/backend.md](../architecture/backend.md) and [docs/backend/](../backend/).
