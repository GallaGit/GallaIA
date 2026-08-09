# Data Models

## Purpose

Separate ORM models (`app/models/`), API schemas (`app/schemas/`), and domain concepts—and explain why those layers must not be conflated.

## Status

Draft

## Scope

- Existing: Empty `app/models/`, `app/schemas/`, and empty `app/db/` scaffold (`base.py`, `session.py`, `migrations/`).
- Planned: Pydantic request/response schemas for Temporada 1 chat; SQLAlchemy models from Temporada 2.
- Future: Additional entities (users, documents, embeddings) as seasons unlock them.

## TODO

- Document naming conventions for schemas vs ORM models.
- Explain when a schema may mirror a model and when it must differ.
- Align with `docs/architecture/database.md` and `docs/database/` when those are filled.
- Do not document concrete tables as Existing until migrations exist.
