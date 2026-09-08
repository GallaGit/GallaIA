# API Architecture

## Purpose

Explain the HTTP API surface between clients and the backend: versioning, health endpoints, errors, and where conventions will grow.

## Status

Draft

## Scope

- Existing:
  - `GET /` — simple ping / static UI entry when built
  - `GET /health` — infra health (unversioned)
  - `GET /api/v1/health` — versioned API health
  - Control plane: `/api/v1/projects|agents|tasks|sessions|inbox` (SQLite)
  - AgentOS package: `/api/v1/agentos/*` — [CONTRACT.md](../agentos/CONTRACT.md)
  - OpenAPI at `/docs`
  - Router composition via `app.include_router(api_router, prefix="/api/v1")`
  - Global `AppError` JSON envelope; `X-Request-ID` on responses
- Planned: Phase 2+ endpoints (grants, templates, goals, webhooks) only when those phases start — [ROADMAP.md](../ROADMAP.md).
- Future: pagination, filtering, richer versioning policy; single-operator auth.

## Related docs

- [docs/backend/routing.md](../backend/routing.md)
- [docs/backend/request-lifecycle.md](../backend/request-lifecycle.md)
- [docs/backend/error-handling.md](../backend/error-handling.md)
- [product/MODULE_BOUNDARIES.md](../product/MODULE_BOUNDARIES.md)

## TODO

- Keep OpenAPI as the live contract for request/response shapes.
- Do not grow [CONTRACT.md](../agentos/CONTRACT.md) for Phase 2+ until implementation starts.
- Drop demo-error from the public surface when no longer useful for learning.
