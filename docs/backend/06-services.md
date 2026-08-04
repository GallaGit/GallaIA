# Services

## Purpose

Describe the service layer as the place for use-case orchestration—why routes call services, and why services do not talk to HTTP or raw SQL directly.

## Status

Draft

## Scope

- Existing: Empty `app/services/` directory.
- Planned: Chat/orchestration service for Temporada 1 (message in → provider call → message out).
- Future: Services for history, RAG, agents, and automations in later seasons.

## TODO

- Define service naming and one-use-case-per-service guidance.
- Clarify boundaries vs repositories and vs AI providers.
- Document error translation from domain/provider failures to API exceptions.
- Add examples after the first service is implemented.
