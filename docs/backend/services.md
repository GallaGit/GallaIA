# Services

## Purpose

Describe the service layer as the place for use-case orchestration—why routes call services, and why services do not talk to HTTP or raw SQL directly.

## Status

Draft

## Scope

- Existing: AgentOS / control-plane services and prompts under `app/services/` and `app/agentos/` (runners, seeds, grants, network policy, filesystem ACL, secret refs, task/session orchestration).
- Active: Template instantiate + goal orchestrator stub (`app/services/goals.py` orchestrate + spend/time/stuck rails).
- Future: RAG, product-chat orchestration, richer automations.

## TODO

- Define service naming and one-use-case-per-service guidance.
- Clarify boundaries vs repositories and vs AI providers / runners.
- Document error translation from domain/provider failures to API exceptions.
- Keep examples tied to AgentOS flows (run task, inbox reply), not a Temporada-1 chat proxy.
