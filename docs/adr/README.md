# Architecture Decision Records

## Purpose

ADRs record **why** significant technical choices were made, so future contributors understand intent—not only the current file tree.

## Status

Draft

## ADR statuses

| Status | Meaning |
|--------|---------|
| Proposed | Under discussion; not yet binding |
| Accepted | Decision stands for the project |
| Deprecated | Superseded or withdrawn |

## Index

| ID | Title | Decision status | Doc status |
|----|-------|-----------------|------------|
| [ADR-001](ADR-001-fastapi.md) | Use FastAPI for the backend HTTP API | Accepted | Final |
| [ADR-002](ADR-002-project-structure.md) | Layered project structure under `app/` | Accepted | Final |
| [ADR-003](ADR-003-postgresql.md) | Use PostgreSQL for persistence | Proposed | Draft |

## TODO

- Accept ADR-003 when cutting over from SQLite to PostgreSQL (infra/Future — not AgentOS “Fase 3”).
- Add new ADRs for other significant choices (ORM details, auth, vector store) when those decisions are made.
- Keep each ADR focused on context, decision, and consequences—not implementation tutorials.
