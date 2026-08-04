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

Documentation draft status (Draft / Final) is separate from ADR decision status.

## Index

| ID | Title | Decision status | Doc status |
|----|-------|-----------------|------------|
| [ADR-001](ADR-001-fastapi.md) | Use FastAPI for the backend HTTP API | Proposed | Draft |
| [ADR-002](ADR-002-postgresql.md) | Use PostgreSQL for persistence | Proposed | Draft |

## TODO

- Move ADRs to Accepted when the corresponding implementation starts and the team confirms the choice.
- Add new ADRs for other significant choices (e.g. ORM, auth, vector store) when those decisions are made.
- Keep each ADR focused on context, decision, and consequences—not implementation tutorials.
