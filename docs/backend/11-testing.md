# Testing

## Purpose

Describe the testing strategy for the backend so tests grow with the codebase: what to test at each layer and why, without over-engineering early.

## Status

Draft

## Scope

- Existing: Empty `backend/tests/` directory.
- Planned: Pytest layout, API tests for chat endpoints, and provider mocking for Temporada 1.
- Future: Integration tests with PostgreSQL, contract tests, and CI gates.

## TODO

- Define test directory layout and naming conventions.
- Clarify unit vs API vs integration scope for this educational project.
- Document how to mock AI providers and avoid real API calls in CI.
- Link to CI docs under `docs/deployment/` when that section is written.
