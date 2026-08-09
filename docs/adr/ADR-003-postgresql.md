# ADR-003: Use PostgreSQL for Persistence

## Status

Proposed (documentation: Draft)

## Context

From the database phase onward (see [ROADMAP.md](../ROADMAP.md) Fase 3), GallaAI needs durable storage for users and later conversation history. The long-term stack names PostgreSQL and SQLAlchemy. Persistence is not required for the current Foundation / API Base work.

## Decision

Use **PostgreSQL** as the primary relational database when persistence is introduced, accessed via **SQLAlchemy** (and migrations under `app/db/migrations/`).

## Consequences

- Strong relational model for users, messages, and future entities.
- Operational overhead (local Docker Postgres, migrations) appears when Fase 3 starts.
- Empty `app/db/` scaffold today must not be described as a live database.
- Vector/RAG storage choices remain Future and may warrant a separate ADR.

## TODO

- Accept this ADR when PostgreSQL is wired for Fase 3.
- Document connection/config conventions in [docs/backend/configuration.md](../backend/configuration.md) and [docs/architecture/database.md](../architecture/database.md).
- Do not treat ADR-003 as implemented until migrations and a running instance exist.
