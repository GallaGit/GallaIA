# Authentication

## Purpose

Record how authentication and authorization will be introduced when user accounts become in scope—without treating auth as part of Temporada 1.

## Status

Draft

## Scope

- Existing: Empty `app/core/security.py` scaffold only.
- Planned: Out of Temporada 1 (see `docs/alcance.md`). Design deferred until persistence/users are needed.
- Future: Authn/authz mechanisms (e.g. tokens, session strategy), password/OAuth choices, and protected routes.

## Notes

This document is **outside** the numbered Temporada 1 backend series (`01`–`11`). It exists so the topic has a home when Temporada 2+ unlocks it.

## TODO

- Decide auth approach when users are in scope (do not invent premature design).
- Document how security helpers in `app/core/security.py` will be used.
- Align with middleware and dependency-injection docs when auth lands.
