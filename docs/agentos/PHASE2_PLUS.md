# AgentOS Phase 2+ — sketch only (do not implement in this PR)

Short roadmap after MVP seeds + mock runner. **Numeración alineada** con [ROADMAP.md](../ROADMAP.md) y [POSTMA_WALKTHROUGH.md](POSTMA_WALKTHROUGH.md) §4. Inspired by the reconstructed Danny Postma AgentOS blueprint; not a commitment to Mac runners or Cursor Cloud Agents.

Sidebar surfaces (Skills, Environment, Connections, Activity, Ripples, Admin, Knowledge, Templates, Goals): see [CONTROL_PLANE_NAV.md](../product/CONTROL_PLANE_NAV.md). **Doc only** — do not implement in the Phase 1 MVP.

## Phase 2 — Isolation

- Per-agent MCP / repo / env grants (default deny)
- Network policy `open` | `limited` + host allowlist at runner proxy
- Filesystem MCP with server-side read/write/delete ACLs and per-agent folders
- Secret refs injected at session start only (no raw tokens in DB)
- UI surfaces that become real here: **Environment**, **Connections**, **Files** (real browser)

**Done when:** a support-style agent with only a fake Front MCP cannot call GitHub or read another agent's folder.

## Phase 3 — Templates (+ gates, chains, Skills CRUD mínimo)

- `TaskTemplate` + instantiate
- Approval gates enforced in API and MCP (not honor-system prompts)
- Follow-up chain scheduler; seed `compound-engineer-workflow` (9 steps)
- Product seed (doc): `lead-intake-workflow` (2 steps, `leadId`) — [LEAD_INTAKE.md](../product/LEAD_INTAKE.md); agents `lead-researcher` / `lead-solutions`
- Schedule-at / recurring cron on tasks
- Skills catalog CRUD mínimo (e.g. `plan-mode` ceases to be a bare seed string only)

**Done when:** instantiating the template creates 9 cards; step 2 does not start until a human marks step 1 `done`; an agent token cannot mark a gated step `done`. (`lead-intake-workflow`: 2 cards; score gate documented in LEAD_INTAKE.)

## Phase 4 — Goals (gauntlet loop)

- Goal + Definition of Done (human-approved before spawn)
- Orchestrator after each session picks next specialist or completes
- Safety rails: spend cap, max wall time, stuck threshold (~19 identical iterations)

**Done when:** a 2-item DoD goal completes via ≥2 specialist sessions; rails stop runaway loops.

## Phase 5 — Triggers (+ automations; Ripples leave theory)

- Public webhook + secret → scoped task + session
- Seed shapes: support-inbound, bug-report → diagnostic then (on human OK) fix chain
- Product seed (doc): `lead-status-nuevo` → instantiate `lead-intake-workflow` — [LEAD_INTAKE.md](../product/LEAD_INTAKE.md)
- Named cron automations
- **Ripples** UI can show cause→effect edges (trigger → task → session, template step → next)
- No Mac-only workers required; runner stays `mock` | Anthropic API | later Linux VM

**Done when:** signed webhook creates task+session; bad secret → 401; a cron fires on a test clock.

## Later (see ROADMAP Fases 6–7)

- **Fase 6** YAML / CLI (`agentos.yml` push/pull) — Admin sync
- **Fase 7** PWA inbox, live viewer, **Activity** feed, local runner routing

## Explicit non-goals for GallaIA now

- Cursor Cloud Agents as the runtime
- Mac-only local runners
- Shipping LangGraph / multi-tenant SaaS as the MVP path
