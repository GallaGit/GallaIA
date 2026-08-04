# ADR-002: Use PostgreSQL for Persistence

## Status

Proposed (documentation: Draft)

## Context

From Temporada 2 onward, GallaAI needs durable storage for conversation history and later product data. Temporada 1 explicitly excludes a database (`docs/alcance.md`). The long-term stack names PostgreSQL and SQLAlchemy.

## Decision

Use **PostgreSQL** as the primary relational database when persistence is introduced, accessed via **SQLAlchemy** (and migrations under `app/db/migrations/`).

## Consequences

- Strong relational model for users, messages, and future entities.
- Operational overhead (local Docker Postgres, migrations) appears only when Temporada 2 starts.
- Empty `app/db/` scaffold today must not be described as a live database.
- Vector/RAG storage choices remain Future and may warrant a separate ADR.

## TODO

- Accept this ADR when PostgreSQL is wired for Temporada 2.
- Document connection/config conventions in [docs/backend/03-configuration.md](../backend/03-configuration.md) and [docs/architecture/database.md](../architecture/database.md).
- Do not treat ADR-002 as implemented until migrations and a running instance exist.
