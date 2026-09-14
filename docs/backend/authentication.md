# Authentication

## Purpose

Record how authentication and authorization are introduced for a **single operator**—without treating full OAuth as part of AgentOS core.

## Status

Draft — lean **actor headers** landed in Phase 3 (gate authz only). Full login still Future.

## Scope

- Existing:
  - Lean request actor via headers (not OAuth / JWT):
    - X-Actor-Type: human | agent — default **human** if omitted (UI / curl).
    - X-Agent-Id: <int> — optional agent id when type is gent.
  - Helpers: pp.core.security.parse_actor_headers / FastAPI ActorDep.
  - Authz: ssert_actor_may_mark_done — agent callers get **403** when marking done on an pproval_gate task or a task with unmet depends_on. Humans may still mark done (prior-step gate still applies).
  - Wired on PATCH /api/v1/tasks/{id}/status and as a belt-and-suspenders check on the control-plane run→done path.
- Planned: Out of Phase 1–3 core (see [alcance.md](../alcance.md)). Single-operator login (CLI token / session cookie) when a public surface needs it.
- Future: Authn/authz for one human; **not** multi-tenant SaaS RBAC as the MVP path.

## Notes

This document is outside the AgentOS Phase 1 core topics. Phase 3 only adds the minimal header convention so "agent token cannot mark gated done" is enforceable without inventing OAuth.

## TODO

- Decide auth approach when a public surface or CLI needs a personal token.
- Align with middleware and dependency-injection docs when full auth lands.
- Do not invent multi-user billing roles for GallaIA MVP.
