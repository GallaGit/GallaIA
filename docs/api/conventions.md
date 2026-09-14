# API conventions

## Actor headers (Phase 3 lean authz)

Not full auth — a header convention so human vs agent callers can be distinguished on status updates.

| Header | Values | Default |
|--------|--------|---------|
| X-Actor-Type | human or gent | human (omit = operator / UI) |
| X-Agent-Id | integer agent id | optional |

**Rules**

- PATCH /api/v1/tasks/{id}/status with {"status":"done"}:
  - **agent** + (pproval_gate or unmet depends_on) → **403** orbidden
  - **human** → allowed (still subject to prior-step BadRequest if dependency unmet)
- Agent runtimes / MCP tools SHOULD send X-Actor-Type: agent.
- Do not build OAuth here; see [authentication.md](../backend/authentication.md).
