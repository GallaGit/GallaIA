# Request Lifecycle

## Purpose

Describe how an HTTP request moves through the app today, so contributors share one mental model before DB, auth, and services exist.

## Status

Draft (reflects current implementation)

## Scope

- Existing: Uvicorn → FastAPI app → (optional route dependency) → handler → JSON response; lifespan configures logging at startup.
- Planned: middleware, global exception handlers, DB session dependency, auth dependency, service layer.
- Future: provider calls, RAG, agents in the path for chat features.

## Current happy path

```text
HTTP request
  → Uvicorn
  → FastAPI routing
  → Depends(get_settings) when declared
  → route handler
  → JSON response
```

Example: `GET /api/v1/health` resolves via `api_router` → `health.router` → `api_health()`, which reads `Settings` through `Depends`.

## Lifespan

On startup: `setup_logging` (from import side) + lifespan `INFO` log.  
On shutdown: lifespan logs shutdown.  
No DB connect/disconnect yet.

## TODO

- Extend the diagram when middleware and exception handlers are added.
- Document failure paths (validation errors, app errors) with [error-handling.md](error-handling.md).
