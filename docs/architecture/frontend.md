# Frontend Architecture

## Purpose

Frame how the Next.js frontend will talk to the backend API for chat, and why UI concerns stay out of the FastAPI layer.

## Status

Draft

## Scope

- Existing: `frontend/` directory present at repo root (implementation not documented here; backend-planning focus).
- Planned: Temporada 1 chat UI calling the backend over HTTP.
- Future: Auth UX, history views, RAG/document UI, dashboard.

## TODO

- Document the planned client → API contract for chat once endpoints exist.
- Clarify env-based API base URL conventions.
- Link to backend routing and API docs when filled.
- Avoid documenting UI frameworks or folder details as Existing until verified.
