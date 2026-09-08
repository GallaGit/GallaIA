# Database Architecture

## Purpose

Capture what persistence exists today (SQLite control plane) and why PostgreSQL remains the long-term relational target when SQLite is no longer enough.

## Status

Draft

## Scope

- Existing: SQLite database for the SQLAlchemy control plane (`data/gallaia.db` / project data path); ORM models and schemas for projects, agents, tasks, sessions, inbox. In-memory store for `/api/v1/agentos/*` (separate surface).
- Planned: Stronger migration workflow (Alembic) as the schema grows with AgentOS phases; **not** “Fase 3 = Postgres” from the old chat roadmap.
- Future: PostgreSQL when SQLite hurts — [ADR-003](../adr/ADR-003-postgresql.md) (Proposed). Vector/RAG storage = separate Future ADR.

## Related decisions

- [ADR-003: PostgreSQL](../adr/ADR-003-postgresql.md) (Proposed)
- Product persistence notes: [AGENTOS.md](../product/AGENTOS.md)

## TODO

- Document engine/session lifecycle for the live SQLite path.
- Align Alembic under `app/db/migrations/` when migrations become first-class.
- Cross-link [docs/backend/repositories.md](../backend/repositories.md) and [data-models.md](../backend/data-models.md).
- Do not list Postgres tables as Existing until Postgres is wired.
