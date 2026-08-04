# Routing

## Purpose

Define how HTTP routes are organized under `app/api/routes/`, how routers are composed in `main.py`, and why route modules stay free of business logic.

## Status

Draft

## Scope

- Existing: Empty `app/api/routes/` and empty `app/api/__init__.py`.
- Planned: Chat (and health) routers for Temporada 1; URL prefixes and OpenAPI tags.
- Future: Versioned or domain-specific routers as the API grows (see also `docs/api/`).

## TODO

- Establish router file naming and include strategy.
- Document request/response schema ownership (Pydantic in `schemas/`).
- Define status-code and error-response conventions at the route boundary.
- Link to `docs/api/` when those guides are written.
