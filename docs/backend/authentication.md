# Authentication

## Purpose

Record how authentication and authorization will be introduced for a **single operator**—without treating auth as part of AgentOS Phase 1.

## Status

Draft

## Scope

- Existing: Empty / light `app/core/security.py` scaffold only. Phase 1 runs without login (localhost / Docker).
- Planned: Out of Phase 1 (see [alcance.md](../alcance.md)). Design deferred until a single-operator gate is needed (CLI token, session cookie).
- Future: Authn/authz for one human; **not** multi-tenant SaaS RBAC as the MVP path.

## Notes

This document is outside the AgentOS Phase 1 core topics. It exists so authentication has a home when the roadmap unlocks it ([ROADMAP.md](../ROADMAP.md) — infra/Future, not “Fase 4 chat-era JWT”).

## TODO

- Decide auth approach when a public surface or CLI needs a personal token.
- Document how security helpers in `app/core/security.py` will be used.
- Align with middleware and dependency-injection docs when auth lands.
- Do not invent multi-user billing roles for GallaIA MVP.
