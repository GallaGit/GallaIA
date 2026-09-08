# Testing

## Purpose

Describe the testing strategy for the backend so tests grow with the codebase: what to test at each layer and why, without over-engineering early.

## Status

Draft

## Scope

- Existing: Backend tests for AgentOS runner / control plane (e.g. `backend/tests/test_agentos_runner.py` and related).
- Planned: Expand API tests for Kanban/inbox/session flows; keep provider calls mocked (no real Anthropic in CI by default).
- Future: Integration tests with PostgreSQL when cutover happens; contract tests; stronger CI gates.

## TODO

- Define test directory layout and naming conventions.
- Clarify unit vs API vs integration scope for this educational project.
- Document how to mock AI providers and avoid real API calls in CI.
- Link to CI docs under `docs/deployment/` when that section is written.
- Prefer AgentOS acceptance ideas from [POSTMA_WALKTHROUGH.md](../agentos/POSTMA_WALKTHROUGH.md) §9 when Phase 2+ lands.
