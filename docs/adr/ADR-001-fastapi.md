# ADR-001: Use FastAPI for the Backend HTTP API

## Status

Accepted

## Context

GallaAI needs a Python HTTP API that will grow from a simple chat proxy into a larger AI platform. The project is educational: clarity, typing, and incremental delivery matter more than exotic architecture.

Candidates considered at a high level include FastAPI, Django, and Flask. The stack target in the product docs already names FastAPI.

## Decision

Use **FastAPI** as the backend web framework.

## Consequences

- Natural fit for Pydantic schemas, OpenAPI, and async I/O with AI provider clients.
- Dependency injection via `Depends` supports a thin-route / service-layer style.
- Team must learn FastAPI conventions (routers, lifespan, exception handlers).
- Confirmed in code: runnable app in `backend/app/main.py`, Settings, logging, health routes, Docker.

## References

- [docs/architecture/backend.md](../architecture/backend.md)
- [docs/backend/](../backend/)
- [backend/README.md](../../backend/README.md)
