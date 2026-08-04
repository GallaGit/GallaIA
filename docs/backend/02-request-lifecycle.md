# Request Lifecycle

## Purpose

Describe how an HTTP request will move through FastAPI middleware, dependencies, routes, services, and responses—so contributors share one mental model before code exists.

## Status

Draft

## Scope

- Existing: Empty `app/main.py`, `app/middleware/`, and `app/api/` scaffold only.
- Planned: Document the Temporada 1 chat request path (HTTP → route → service → AI provider → response).
- Future: Persistence, auth, and RAG steps in the lifecycle when those seasons begin.

## TODO

- Diagram the planned happy-path lifecycle for a chat message.
- List extension points (middleware, dependencies, exception handlers).
- Clarify where validation, orchestration, and side effects belong.
- Update this doc when `main.py` and the first route are implemented.
