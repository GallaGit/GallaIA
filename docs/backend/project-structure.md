# Project Structure

## Purpose

Explain why the backend uses a layered package layout under `backend/app/`, what each package owns, and how that layout supports incremental growth without premature complexity.

## Status

Draft

## Scope

- Existing: Empty directory scaffold under `backend/app/` (api, core, db, models, schemas, repositories, services, providers, agents, tools, memory, rag, middleware, exceptions, utils, main.py).
- Planned: Document package responsibilities and import boundaries for Temporada 1 (chat API).
- Future: Document how reserved packages (agents, rag, memory, tools) activate in later seasons.

## TODO

- Map each `app/` package to a single responsibility and ownership rule.
- Define allowed dependency directions between layers (api → services → repositories → models).
- Document what must not live in each package (e.g. business logic in routes).
- Keep the layout layered; do not migrate to feature-based, hexagonal, CQRS, or DDD.
