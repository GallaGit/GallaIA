# Request Lifecycle

## Purpose

Describe how an HTTP request moves through the app today, so contributors share one mental model before DB, auth, and services exist.

## Status

Draft (reflects current implementation)

## Scope

- Existing: Uvicorn → request-id middleware → FastAPI routing → dependencies → handler → JSON response; AppError handlers on failure; lifespan configures logging at startup.
- Planned: DB session dependency, auth dependency, service layer.
- Future: provider calls, RAG, agents in the path for chat features.

## Current happy path

```text
HTTP request
  → Uvicorn
  → RequestIdMiddleware (log + X-Request-ID)
  → FastAPI routing
  → Depends (e.g. SettingsDep) when declared
  → route handler
  → AppError / unhandled handlers if raised
  → JSON response (+ X-Request-ID header)
```

Example: `GET /api/v1/health` resolves via `api_router` → `health.router` → `api_health()` with `SettingsDep`.

## Lifespan

On startup: `setup_logging` (from import side) + lifespan `INFO` log.  
On shutdown: lifespan logs shutdown.  
No DB connect/disconnect yet.

## Failure path

See [error-handling.md](error-handling.md). Application errors return `{ "error": { "code", "message" } }`.

## TODO

- Extend the diagram when DB/auth dependencies join the path.
