# AgentOS Phase 2+ — Isolation complete; Phase 3 Templates core done

Short roadmap after MVP seeds + mock runner. **Numeración alineada** con [ROADMAP.md](../ROADMAP.md) y [POSTMA_WALKTHROUGH.md](POSTMA_WALKTHROUGH.md) §4. Inspired by the reconstructed Danny Postma AgentOS blueprint; not a commitment to Mac runners or Cursor Cloud Agents.

**En curso:** **Phase 4 Goals** (slice 2: orchestrator stub + safety rails — done-when stub path met; polish left). Phase 3 Templates **core done**. Phase 2 Isolation **done**. UI Files / Connections remain follow-ups.

Sidebar surfaces (Skills, Environment, Connections, Activity, Ripples, Admin, Knowledge, Templates, Goals): see [CONTROL_PLANE_NAV.md](../product/CONTROL_PLANE_NAV.md). **Doc only** until the matching AgentOS phase.

Cadencia autónoma (slices ~1 h, docs Hecho/Por hacer antes de cada PR): [ROADMAP.md](../ROADMAP.md) § Operación autónoma.

## Phase 2 — Isolation **done**

| Muro | Estado |
|------|--------|
| Per-agent MCP / repo / env grants (default deny) | **Done** |
| Network policy `open` \| `limited` + host allowlist at runner proxy | **Done** |
| Filesystem MCP with server-side read/write/delete ACLs and per-agent folders | **Done** |
| Secret refs injected at session start only (no raw tokens in DB) | **Done** (este PR) |
| UI surfaces: **Environment**, **Connections**, **Files** (real browser) | Follow-up — **no bloquea Isolation** |

**Done when (grants wall):** a support-style agent with only a fake Front MCP cannot call GitHub.

**Done when (network wall):** `limited` + allowlist `api.front.com` cannot `http.fetch` `api.github.com`; `open` can.

**Done when (filesystem wall):** Agent A cannot `fs.read` Agent B's `/agents/{b}/` folder; `../` is denied.

**Done when (secret refs):** agents store name/key pointers; session start resolves from process env (or test fixture); unresolved ref denies; SQLite dump has no secret plaintext.

**Isolation complete.** Leftover UI (Files / Connections) does not block this phase.

## Phase 3 — Templates (+ gates, chains, Skills CRUD) — **core done**

### Slice 1 — Hecho (merged #18)

- `TaskTemplate` + `TaskTemplateStep` in SQLite; instantiate API
- Seed `demo-two-step` (2 steps): step 1 approval gate; step 2 `requires_previous_done`
- Gate enforced in run / status / mock runner
- Pytest: 2 cards; step 2 blocked until step 1 `done`

### Slice 2 — Hecho (merged #19)

- Seed `compound-engineer-workflow` (9 steps, POSTMA §2.8); steps 2–9 `requires_previous_done`; gates on 1 and 9
- Instantiate → 9 cards with `depends_on` chain
- Pytest: count=9; step 2 blocked until 1 `done`; step 3 blocked until 2 `done`

### Slice 3 — Hecho (merged #20)

- SQLite `Skill` catalog (`slug` / `name` / `description` / `kind` / `body`) + seed `plan-mode`
- API list/get/create/patch/put-upsert/delete under `/api/v1/skills`
- Minimal glue: `AgentSeed.skills` stay as slugs; agentos list/get fills `resolved_skills` from catalog
- Pytest: seed + CRUD + agent slug resolve

### Slice 4 — Hecho (merged #21)

- Product seed `lead-intake-workflow` (2 steps, `leadId`): step 2 `requires_previous_done` + approval gate
- Lean agent seeds `lead-researcher` / `lead-solutions` (GallaAI product prompts)
- Pytest: instantiate → 2 cards + prior-step gate; assignees resolve

### Slice 5 — schedule-at (merged #22)

**Hecho**

- Task.scheduled_at + PATCH /tasks/{id}/schedule + POST /scheduler/tick (optional now test clock)
- Due tasks cleared + session stub (runner=scheduler, status=queued) when assignee set
- Pytest: future not due; past promoted; cron deferred to Phase 5 (skipped test)

### Slice 6 (este PR) — agent token cannot mark gated done

**Hecho**

- Lean headers X-Actor-Type: human|agent (default human) + optional X-Agent-Id — no OAuth
- Agent PATCH status to done on approval_gate or unmet depends_on → **403**; human allowed
- Run path belt-and-suspenders; pytest agent denied + human allowed
- Docs: authentication.md + api/conventions.md

**Phase 3 core done-when: satisfied** (agent cannot mark gated done; schedule-at landed; cron = Phase 5).

### Por hacer (optional / next phases)

- Compound assignee agents (missing role seeds: spec, 
eview-coordinator, etc.) — optional polish
- Cron runner / named automations — **Phase 5**
- Phase 4 Goals → **near done** (slice 2 orchestrator+rails)
- UI Templates / Skills surfaces

**Done when (full Phase 3):** instantiating compound creates 9 cards; step 2 does not start until a human marks step 1 done; an agent token cannot mark a gated step done — **met**. (lead-intake-workflow: 2 cards; score gate documented in LEAD_INTAKE.)

**Slice 2 done when:** instantiate `compound-engineer-workflow` → 9 cards; step 2/3 gated on prior `done`.

## Phase 4 — Goals (gauntlet loop) *(near done)*

### Slice 1 — foundation (merged #24)

- SQLite `Goal` + DoD items (JSON list); status `draft|approved|active|done`
- API create / list / get / approve / spawn stub
- Spawn blocked until human approve (`draft` → 400)
- Pytest: unapproved blocked; approve → placeholder session + task link

### Slice 2 — orchestrator stub + safety rails (este PR)

- Rails: `spend_cap` / `spend_accrued` / `max_wall_seconds` / `stuck_threshold` (default 19); `dod_checked`; status `stuck`
- `POST /api/v1/goals/{id}/orchestrate` advances one step (complete open session → check DoD → spawn next or `done`)
- Cap `0.00` → **403**; wall exceeded → **400**; last N identical summaries → `stuck`
- Pytest: 2-item DoD → ≥2 sessions → done; cap + stuck + HTTP

### Por hacer (polish — no este PR)

- Progress log / goal inbox / runnerPreference
- Real specialist routing + auto-hook after live session end
- Spend accrual from real provider usage

**Done when (full Phase 4):** a 2-item DoD goal completes via ≥2 specialist sessions; rails stop runaway loops — **met on stub path**.

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
