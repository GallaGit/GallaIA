# Database Architecture

## Purpose

Capture why PostgreSQL and SQLAlchemy are the planned persistence stack, and when they enter the system relative to the product roadmap.

## Status

Draft

## Scope

- Existing: Empty `app/db/` scaffold (`base.py`, `session.py`, `migrations/`); no live database, no migrations content.
- Planned: PostgreSQL + SQLAlchemy from Temporada 2 (persistence and history per `docs/alcance.md`). Not required for Temporada 1 chat.
- Future: Indexing, richer relationships, and operational concerns — see empty stubs under `docs/database/`.

## Related decisions

- [ADR-003: PostgreSQL](../adr/ADR-003-postgresql.md) (Proposed)

## TODO

- Document engine/session lifecycle when `db/session.py` is implemented.
- Align migration workflow with Alembic under `app/db/migrations/`.
- Do not list tables or indexes as Existing until they exist in code.
- Cross-link [docs/backend/repositories.md](../backend/repositories.md) and [data-models.md](../backend/data-models.md).
