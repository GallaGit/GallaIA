# Repositories

## Purpose

Explain why data access will be isolated behind repositories, keeping persistence details out of services and routes.

## Status

Draft

## Scope

- Existing: Empty `app/repositories/` directory; no database runtime.
- Planned: Repository pattern when persistence starts (Temporada 2 per `docs/alcance.md`).
- Future: Richer query helpers, transactions spanning multiple aggregates if needed.

## TODO

- Document repository interface conventions (methods, return types).
- Clarify relationship to SQLAlchemy models and sessions.
- State that Temporada 1 may run without repositories until persistence is in scope.
- Avoid implying a live database exists today.
