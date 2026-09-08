# Repositories

## Purpose

Explain why data access is isolated behind repositories (or equivalent data helpers), keeping persistence details out of routes where practical.

## Status

Draft

## Scope

- Existing: SQLite-backed control plane data access for AgentOS entities (see `app/models`, services, routes). In-memory store for `/api/v1/agentos/*`.
- Planned: Clearer repository boundaries as Isolation / templates / goals schemas grow — [ROADMAP.md](../ROADMAP.md).
- Future: Postgres session patterns when ADR-003 is accepted.

## TODO

- Document repository interface conventions (methods, return types).
- Clarify relationship to SQLAlchemy models and sessions.
- Avoid implying PostgreSQL is required for Phase 1.
