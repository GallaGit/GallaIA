# API Architecture

## Purpose

Explain the HTTP API surface between clients and the backend: versioning, health endpoints, errors, and where conventions will grow.

## Status

Draft

## Scope

- Existing:
  - `GET /` — simple ping
  - `GET /health` — infra health (unversioned)
  - `GET /api/v1/health` — versioned API health
  - `GET /api/v1/demo-error` — learning-only error demo
  - OpenAPI at `/docs`
  - Router composition via `app.include_router(api_router, prefix="/api/v1")`
  - Global `AppError` JSON envelope; `X-Request-ID` on responses
- Planned: domain endpoints (users, auth, chat, …).
- Future: pagination, filtering, richer versioning policy.

## Related docs

- [docs/backend/routing.md](../backend/routing.md)
- [docs/backend/request-lifecycle.md](../backend/request-lifecycle.md)
- [docs/backend/error-handling.md](../backend/error-handling.md)

## TODO

- Keep OpenAPI as the live contract for request/response shapes.
- Drop demo-error from the public surface when Fase 3+ starts in earnest.
