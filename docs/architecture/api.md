# API Architecture

## Purpose

Explain the planned HTTP API surface between frontend and backend: resource style, error shape, and where detailed conventions will live.

## Status

Draft

## Scope

- Existing: No implemented endpoints; empty `app/api/routes/`.
- Planned: REST-style chat (and health) endpoints for Temporada 1.
- Future: Pagination, filtering, versioning, and richer resources — detail stubs under `docs/api/`.

## Related docs

- Deep routing notes: [docs/backend/05-routing.md](../backend/05-routing.md)
- Future detail: `docs/api/` (conventions, endpoints, pagination, filtering, versioning) — scaffolding only today.

## TODO

- Summarize resource naming and status-code policy once the first routes exist.
- Link OpenAPI as the source of truth for request/response schemas.
- Keep this doc architectural; leave endpoint catalogs to `docs/api/endpoints.md`.
