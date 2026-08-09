# API Architecture

## Purpose

Explain the HTTP API surface between clients and the backend: versioning, health endpoints, and where conventions will grow.

## Status

Draft

## Scope

- Existing:
  - `GET /` — simple ping
  - `GET /health` — infra health (unversioned)
  - `GET /api/v1/health` — versioned API health
  - OpenAPI at `/docs`
  - Router composition via `app.include_router(api_router, prefix="/api/v1")`
- Planned (Fase 2 remainder): global error shape, middleware, shared dependencies; then domain endpoints (users, chat, …).
- Future: pagination, filtering, richer versioning policy — detail stubs may live under `docs/api/` if/when filled.

## Related docs

- [docs/backend/routing.md](../backend/routing.md)
- [docs/backend/request-lifecycle.md](../backend/request-lifecycle.md)

## TODO

- Document status-code and error body policy when exception handlers land.
- Keep OpenAPI as the live contract for request/response shapes.
