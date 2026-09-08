# Data Models

## Purpose

Separate ORM models (`app/models/`), API schemas (`app/schemas/`), and domain concepts—and explain why those layers must not be conflated.

## Status

Draft

## Scope

- Existing: SQLAlchemy models and Pydantic schemas for the AgentOS control plane (projects, agents, tasks, sessions, inbox) plus in-memory AgentOS package schemas under `app/agentos/`.
- Planned: Models/schemas for Isolation grants, templates, goals, triggers when those phases start — [ROADMAP.md](../ROADMAP.md).
- Future: Users (single-operator auth), documents/embeddings if RAG lands.

## TODO

- Document naming conventions for schemas vs ORM models.
- Explain when a schema may mirror a model and when it must differ.
- Align with [docs/architecture/database.md](../architecture/database.md).
- Do not document Postgres tables as Existing until ADR-003 is implemented.
