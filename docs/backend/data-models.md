# Data Models

## Purpose

Separate ORM models (`app/models/`), API schemas (`app/schemas/`), and domain concepts—and explain why those layers must not be conflated.

## Status

Draft

## Scope

- Existing: SQLAlchemy models and Pydantic schemas for the AgentOS control plane (projects, agents, grants, network, filesystem ACL, secret refs, tasks, templates, skills, goals, sessions, inbox, triggers webhook schemas, automations) plus in-memory AgentOS package schemas under `app/agentos/`.
- Planned: Ripples edges / richer cron-string fields — [ROADMAP.md](../ROADMAP.md).
- Future: Users (single-operator auth), documents/embeddings if RAG lands.

## TODO

- Document naming conventions for schemas vs ORM models.
- Explain when a schema may mirror a model and when it must differ.
- Align with [docs/architecture/database.md](../architecture/database.md).
- Do not document Postgres tables as Existing until ADR-003 is implemented.
