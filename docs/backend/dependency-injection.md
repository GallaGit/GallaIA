# Dependency Injection

## Purpose

Explain why FastAPI dependencies are the preferred wiring mechanism for shared resources (settings, DB sessions, providers) and how that keeps routes thin.

## Status

Draft

## Scope

- Existing: Empty `app/api/dependencies/` directory.
- Planned: Dependency providers for settings and AI client(s) in Temporada 1.
- Future: DB session, auth context, and richer provider factories in later seasons.

## TODO

- Define naming and placement conventions for dependency callables.
- Document lifetime expectations (request-scoped vs app-scoped).
- Show how services receive dependencies without importing infrastructure in routes.
- Update with concrete examples once the first dependencies land.
