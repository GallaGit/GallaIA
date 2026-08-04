# Error Handling

## Purpose

Define a consistent approach to application errors, HTTP mapping, and exception handlers so clients and logs behave predictably.

## Status

Draft

## Scope

- Existing: Empty `app/exceptions/` directory.
- Planned: Custom exception types and FastAPI handlers for Temporada 1 API errors.
- Future: Richer error codes, validation detail policies, and provider-specific failure catalogs.

## TODO

- Propose a small exception hierarchy (e.g. not found, validation, upstream provider).
- Map exceptions to HTTP status codes and response body shape.
- Document what is safe to expose to clients vs what stays in logs.
- Wire guidance to `app/middleware/` if request-id or similar context is added.
