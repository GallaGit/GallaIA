# AgentOS Phase 2+ — sketch only (do not implement in this PR)

Short roadmap after MVP seeds + mock runner. Inspired by the reconstructed Danny Postma AgentOS blueprint; not a commitment to Mac runners or Cursor Cloud Agents.

## Phase 2 — Isolation

- Per-agent MCP / repo / env grants (default deny)
- Network policy `open` | `limited` + host allowlist at runner proxy
- Filesystem MCP with server-side read/write/delete ACLs and per-agent folders
- Secret refs injected at session start only (no raw tokens in DB)

**Done when:** a support-style agent with only a fake Front MCP cannot call GitHub or read another agent's folder.

## Phase 3 — Goals (gauntlet loop)

- Goal + Definition of Done (human-approved before spawn)
- Orchestrator after each session picks next specialist or completes
- Safety rails: spend cap, max wall time, stuck threshold (~19 identical iterations)

**Done when:** a 2-item DoD goal completes via ≥2 specialist sessions; rails stop runaway loops.

## Phase 4 — Triggers

- Public webhook + secret → scoped task + session
- Seed shapes: support-inbound, bug-report → diagnostic then (on human OK) fix chain
- No Mac-only workers required; runner stays `mock` | Anthropic API | later Linux VM

**Done when:** signed webhook creates task+session; bad secret → 401.

## Explicit non-goals for GallaIA now

- Cursor Cloud Agents as the runtime
- Mac-only local runners
- Shipping LangGraph / multi-tenant SaaS as the MVP path
