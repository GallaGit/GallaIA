# ADR-003: Use PostgreSQL for Persistence

## Status

Proposed (documentation: Draft)

## Context

GallaIA’s AgentOS Phase 1 control plane already uses **SQLite** for durable domain objects. The long-term stack still names **PostgreSQL** + SQLAlchemy for when concurrency, ops, or multi-process deploy outgrow SQLite. Postgres is **not** “Fase 3” of the AgentOS roadmap ([ROADMAP.md](../ROADMAP.md)); it is infra/Future outside AgentOS phase numbers.

## Decision

Use **PostgreSQL** as the primary relational database **when** persistence needs outgrow SQLite, accessed via **SQLAlchemy** (and migrations under `app/db/migrations/`). Until then, SQLite remains the Existing control-plane store.

## Consequences

- Strong relational model for AgentOS entities (and later users/messages if product chat returns).
- Operational overhead (Docker Postgres, migrations) appears only when the cutover starts.
- Do not describe empty or unused Postgres scaffolding as a live database.
- Vector/RAG storage choices remain Future and may warrant a separate ADR.

## TODO

- Accept this ADR when PostgreSQL is wired for a real cutover.
- Document connection/config conventions in [docs/backend/configuration.md](../backend/configuration.md) and [docs/architecture/database.md](../architecture/database.md).
- Do not treat ADR-003 as implemented until migrations and a running Postgres instance exist.
