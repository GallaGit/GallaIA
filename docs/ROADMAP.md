# Roadmap — GallaIA AgentOS

**Fuente de verdad del calendario de producto.** Numeración **Fase N = AgentOS**. No usar “Fase 3” para Postgres, chat u otros planes antiguos.

Mapa de producto Phase 1: [product/AGENTOS.md](product/AGENTOS.md).  
Orden de réplica Postma: [agentos/POSTMA_WALKTHROUGH.md](agentos/POSTMA_WALKTHROUGH.md) §4.  
Sketch post-MVP: [agentos/PHASE2_PLUS.md](agentos/PHASE2_PLUS.md).  
Sidebar (doc only): [product/CONTROL_PLANE_NAV.md](product/CONTROL_PLANE_NAV.md).  
Contrato API MVP: [agentos/CONTRACT.md](agentos/CONTRACT.md).

> El plan antiguo Foundation → Postgres → auth → users → **chat** está **cerrado**. No decidir sprints con esa lista.

---

## Operación autónoma (desde 2026-09-14)

Ociel concedió autonomía al Product Manager / Cloud Agent sobre este repo. Cada slice debe ser **pequeño, valorado y testeado**.

| Regla | Detalle |
| ----- | ------- |
| **Cadencia** | Cada **2 días a las 09:00 Europe/Berlin** |
| **Tope** | **Máx. ~1 h por slice** — un PR acotado, no un mega-diff |
| **Créditos** | Usar créditos **Grok primero** hasta ~**85%**; después Cloud Agents |
| **Antes del PR** | Documentar **Hecho** y **Por hacer** (este archivo u otro doc de slice) **antes** de abrir el PR |
| **Merge** | Solo si está **testeado** (docs: `python scripts/check-md-links.py`; código: tests existentes rápidos en verde) |
| **Parar** | Pedir a Ociel **solo** auth / secrets / permisos. No inventar deploy ni tocar secretos |
| **Fuera de slice** | No Isolation runtime “de pasada”; no Leads_CRM, Preparto, multiagente, Demo Waitlist |

### Higiene de PRs abiertos

- [x] **PR #12** (`feature/agent-skills`) — **cerrar, no mergear.** ~357 files / +200k líneas; casi todo es árbol vendored en `.agents/skills` (lock + junk). Reemplazo lean: [agentos/SKILLS.md](agentos/SKILLS.md) (`npx skills add`, sin commitear 200k líneas).

### Slice 2026-09-14 (higiene / cadencia)

**Hecho**

- Cadencia autónoma y reglas de merge/créditos documentadas aquí.
- Fase **2 Isolation** marcada como siguiente *implementación* (sigue siendo spec hasta un PR de runtime dedicado).
- Skills de código: instrucciones `npx skills add` en vez de vendor.
- Decisión de no mergear #12.

**Por hacer (próximos slices, no este PR)**

- Primer PR de **runtime Isolation** (un solo muro: grants default-deny, network policy, o filesystem ACL).
- Instalar skills.sh en la máquina local cuando haga falta (no en git).
- Auth / secrets / deploy solo con Ociel.

---

### Slice Isolation 1 — Grants wall

**Hecho**

- Modelo de grants por agente en SQLite (`agent_grants`: MCP / repo path / env key). Default deny.
- Seed `support` con solo MCP Front fake; mock runner rechaza `github.*`.
- API mínima GET/PUT grants: `/api/v1/agents/{id}/grants` y `/api/v1/agentos/agents/{name}/grants`.
- Tests pytest: default-deny + Front-only no usa GitHub.

---

### Slice Isolation 2 — Network policy

**Hecho**

- `network_mode` `open` | `limited` + host allowlist por agente (`agent_network_policies`).
- Proxy mock `http.fetch`: `limited` deniega hosts fuera de la allowlist; `open` permite.
- Seed `support` en `limited` con `api.front.com`; fetch a GitHub denegado.
- API mínima GET/PUT: `/api/v1/agents/{id}/network` y `/api/v1/agentos/agents/{name}/network`.
- Tests pytest: deny outside allowlist + persistencia SQLite.

---

### Slice Isolation 3 — Filesystem ACL

**Hecho**

- Filesystem MCP mock (`fs.read` / `fs.write` / `fs.delete`) con ACL server-side por agente (`agent_fs_acls`: root + can_read/can_write/can_delete). Default deny fuera de roots.
- Carpeta por agente `/agents/{name}`; Agent A no lee la carpeta de Agent B; `../` denegado (sin resolver).
- API mínima GET/PUT: `/api/v1/agents/{id}/fs` y `/api/v1/agentos/agents/{name}/fs`.
- Tests pytest: allow propio + deny peer + deny `../` + persistencia SQLite.

**Por hacer (siguientes muros Isolation — no este PR)**

- Secret refs inyectados al start (sin tokens crudos en DB) / UI de Connections. → **hecho en slice 4**.
- File browser UI (Environment / Files). → follow-up, no bloquea Isolation.

---

### Slice Isolation 4 — Secret refs (este PR)

**Hecho**

- Secret refs por agente en SQLite (`agent_secret_refs`: `name` + `provider=env` + `key`). Nunca valores plaintext.
- Resolución al start de sesión desde process env (o fixture de test). Ref sin valor → deny/error claro (`unresolved secret ref`).
- PUT rechaza tokens crudos (`sk-…`, `ghp_…`, campo `value`). GET/PUT devuelven nombres/keys, no valores.
- API mínima: `GET/PUT /api/v1/agents/{id}/secrets` y `GET/PUT /api/v1/agentos/agents/{name}/secrets`.
- Tests pytest: persistir solo refs; sesión recibe valor de `GALLAIA_TEST_SECRET_FOO`; dump SQLite sin plaintext.

**Por hacer (no bloquean Isolation done-when)**

- UI **Files** (browser real) y **Connections** (MCP/repos/secret refs).
- R2 / proveedor de secretos local distinto de process env.

**Phase 2 Isolation: complete** al aterrizar este muro. Siguiente fase: Templates.


### Slice Phase 3.1 — TaskTemplate + instantiate + gate

**Hecho** (merged #18)

- Modelo `TaskTemplate` / `TaskTemplateStep` en SQLite + campos de enlace en `tasks`.
- Seed lean `demo-two-step` (2 pasos) + gate prior-step.
- API list/get/instantiate; gate en API/runner.

### Slice Phase 3.2 — compound-engineer seed

**Hecho** (merged #19)

- Seed `compound-engineer-workflow` (9 pasos, POSTMA §2.8): cada paso tras el 1 con `requires_previous_done`; gates en 1 y 9.
- Instantiate → 9 cards con cadena `depends_on`; pytest: count=9, step 2 bloqueado hasta 1 `done`, step 3 bloqueado hasta 2 `done`.

### Slice Phase 3.3 — Skills catalog CRUD

**Hecho** (merged #20)

- Modelo SQLite `Skill` (`slug` / `name` / `description` / `kind` / `body`) + seed `plan-mode`.
- API CRUD (+ PUT upsert) bajo `/api/v1/skills`.
- Glue mínimo: `AgentSeed.skills` sigue siendo slugs; list/get agentos resuelve `resolved_skills` desde el catálogo.
- Pytest: seed + CRUD + resolve de slugs de agents.

### Slice Phase 3.4 — lead-intake-workflow seed (merged #21)

**Hecho**

- Seed `lead-intake-workflow` (2 pasos, variable típica `leadId`): step 1 `lead-researcher`; step 2 `lead-solutions` con gate (`requires_previous_done` + `approval_gate`).
- Lean agent seeds `lead-researcher` / `lead-solutions` (GallaAI product prompts; MCP `crm` grant stub).
- Pytest: instantiate → 2 cards + dependency gate; assignees resuelven.

**Por hacer (siguientes slices Phase 3 — no este PR)**

- Assignee agents for compound steps (roles seed faltantes: `spec`, `review-coordinator`, etc.).
- Gate "token de agente no puede PATCH done" en paso gated (auth/actor). → **hecho en slice 3.6**.
- UI Templates / Skills.
- Phase 3 close criteria: agent token no marca gated `done`; schedule/cron aterrizado o explícitamente deferred.


### Slice Phase 3.5 — schedule-at on tasks (merged #22)

**Hecho**

- Campo Task.scheduled_at (datetime opcional, indexado) + ALTER lean en init_db para SQLite existente.
- API PATCH /api/v1/tasks/{id}/schedule para set/clear; TaskOut expone scheduled_at.
- Demo tick POST /api/v1/scheduler/tick (body opcional now para test clock): promueve due (scheduled_at <= now), limpia schedule, crea session stub runner=scheduler / status=queued si hay assignee.
- Pytest: future no due; past promovido + stub; clear; sin assignee sin session. Cron string runner **deferred** a Phase 5 (test skipped documentado).

### Slice Phase 3.6 — agent token cannot mark gated done (este PR)

**Hecho**

- Lean actor headers: X-Actor-Type: human|agent (default human) + optional X-Agent-Id — no OAuth.
- Authz: agent → **403** on PATCH .../status → done when approval_gate or unmet depends_on; human still allowed (prior-step gate unchanged).
- Run→done path: belt-and-suspenders assert_actor_may_mark_done for agent actor (gated stays in review).
- Pytest: agent denied + human allowed (+ HTTP 403/200); unmet dependency denied for agent.
- Docs: [authentication.md](backend/authentication.md), [api/conventions.md](api/conventions.md).

**Phase 3 core done-when: satisfied** (agent token cannot mark gated done; schedule-at landed; cron recurrence = Phase 5).

**Por hacer (optional polish / next phases — no este PR)**

- Compound assignee agents (roles seed faltantes: spec, 
eview-coordinator, etc.) — optional polish.
- Cron runner / named automations — **Phase 5**.
- Phase 4 Goals → **near done** (slice 4.2 orchestrator+rails; polish left).
- UI Templates / Skills.

---

### Slice Phase 4.1 — Goals foundation (merged #24)

**Hecho**

- Modelo SQLite `Goal` (`name`, `status` draft|approved|active|done, DoD items como JSON list de strings).
- API: `POST/GET /api/v1/goals`, `GET /api/v1/goals/{id}`, `POST .../approve` (draft→approved), `POST .../spawn` stub.
- Spawn gate: unapproved (`draft`) → **400**; approved → placeholder `AgentSession` (`runner=goal-spawn`) + task link; goal → `active`.
- Pytest: cannot spawn unapproved; approve then spawn creates session/task link; HTTP 400/201.

### Slice Phase 4.2 — Orchestrator stub + safety rails (merged #25)

**Hecho**

- Rails on Goal: `spend_cap`, `spend_accrued`, `max_wall_seconds`, `stuck_threshold` (default 19); `dod_checked` parallel to DoD; status `stuck`.
- `POST /api/v1/goals/{id}/orchestrate`: completes open session stub → checks next DoD → spawns next specialist or marks `done`.
- Cap `0.00` → **403** on spawn/orchestrate; wall exceeded → **400**; last N identical session summaries → status `stuck`.
- Pytest: 2-item DoD completes via ≥2 sessions; cap 0.00 rejects; stuck rail; HTTP orchestrate + 403.
- Phase 4 done-when (DoD ≥2 sessions + cap 0.00 + stuck/wall rails) **met** for stub path.

**Por hacer (siguientes slices Phase 4 — no este PR)**

- Progress log append-only / goal inbox / `runnerPreference` por goal.
- Real specialist routing (not stub summaries); auto-hook after live session end.
- Spend accrual from real provider usage (not stub `STUB_SESSION_COST`).


### Slice Phase 5.1 — Signed webhook trigger (merged #26)

**Hecho**

- Config: `GALLAIA_WEBHOOK_SECRET` → `Settings.gallaia_webhook_secret` (empty = deny).
- `POST /api/v1/triggers/webhook` with header `X-Webhook-Secret` (constant-time compare).
- Valid secret → task + session stub (`runner=webhook`, `status=queued`); shapes `generic` / `support-inbound` / `bug-report`.
- Bad/missing/unconfigured secret → **401** (`UnauthorizedError`).
- Pytest: valid path creates task+session; bad/missing → 401; support-inbound assigns `support`.

### Slice Phase 5.2 — Named interval automations + test clock (merged #27)

**Hecho**

- SQLite `Automation` (`name`, `interval_minutes`, `enabled`, `last_fired_at`, JSON action payload).
- API CRUD: `GET/POST /api/v1/automations`, `GET/PATCH/DELETE /api/v1/automations/{id}`.
- `POST /api/v1/automations/tick` with optional `now` (test clock): due → create_task + session stub (`runner=automation`).
- Lean schedule: `interval_minutes` only (no croniter). First fire when `last_fired_at` is null.
- Pytest: due on test clock creates task+session; not-due / disabled do not; HTTP CRUD + tick.

### Slice Phase 5.3 — lead-status-nuevo → lead-intake-workflow (merged #28)

**Hecho**

- `POST /api/v1/triggers/lead-status-nuevo` with `X-Webhook-Secret` + body `{ leadId }`.
- Valid → instantiate seed template `lead-intake-workflow` (2 task cards) for that leadId.
- Bad/missing secret → **401**; missing/blank `leadId` → **400**.
- Pytest: 401, 400, 200 with 2 tasks created.

**Phase 5 core done-when: satisfied** (webhook + cron/interval + lead-status-nuevo).

---

### Slice Phase 6.1 — agentos.yml export/import (merged #29)

**Hecho**

- Minimal `agentos.yml` schema v1 (agents + templates) documented in [agentos/AGENTOS_YML.md](agentos/AGENTOS_YML.md).
- Module `app.services.agentos_yml`: export agents/templates → YAML; import/apply upsert by agent `name` / template `slug`.
- Tiny CLI: `python -m app.cli export` / `import` (from `backend/`).
- Pytest: import creates matching agent+template; idempotent update; export→import round-trip.

### Slice Phase 6.2 — CLI create/update (este PR)

**Hecho**

- `python -m app.cli create-agent --name … --role …` (or `--from-yaml` snippet) — same Agent row shape as YAML import / `GET /api/v1/agents`.
- `python -m app.cli update-agent --name …` partial fields (`--role` / `--title` / `--model` / …).
- Optional `create-template` (lean); bulk templates stay on `import`/`push`.
- Aliases `pull`=`export`, `push`=`import`.
- Pytest + CLI subprocess smoke (create → update → export contains agent).

**Phase 6 core done-when: satisfied** (push/pull + CLI create/update produce same agents+templates as UI list).

**Por hacer (next — Phase 7 / polish)**

- Phase 7 PWA / live.
- Optional: YAML skills/grants/network/fs/secrets; goal/task/skill CLI; Ripples UI; croniter; leadId idempotency polish.


## Fases AgentOS

### Hecho

| Fase | Nombre | Qué incluye | Done when |
|------|--------|-------------|-----------|
| **0** | Foundation | FastAPI, Settings, logging, health, Docker / Compose, `/api/v1`, errores, middleware | App abre, health ok |
| **1** | AgentOS MVP | Seeds `default` / `plan` / `senior-dev`, Kanban, sessions, inbox, mock runner, stub Anthropic Messages, UI atelier | Crear task → run → Kanban avanza → session con tool log |
| **2** | Isolation | Grants MCP/repo/env (default deny), network `open`\|`limited`, filesystem MCP + ACL, secret refs | Support Front-only no llama GitHub ni fetch fuera de allowlist ni lee carpeta ajena; secret refs sin plaintext en DB |

Detalle Phase 1: [product/AGENTOS.md](product/AGENTOS.md). Isolation: [PHASE2_PLUS.md](agentos/PHASE2_PLUS.md) §Phase 2.

### Siguiente

**Fase 3 Templates: core done**. **Fase 4 Goals: near done** (slice 4.2 merged #25; stub done-when met; polish left). **Fase 5 Triggers: core done** (merged #26–#28). **Fase 6 YAML/CLI: core done** (export/import + CLI create/update). Isolation (Phase 2) **done**. UI Files/Connections / Ripples follow-up.

| Fase | Nombre | Qué incluye | Done when (cuando se implemente) |
| ------ | -------- | ------------- | ---------------------------------- |
| **3** | Templates *(core done)* | Slices 1-6: templates + Skills + lead-intake + schedule-at + **agent token gate**. Optional: compound assignee seeds. Cron = Phase 5. ([LEAD_INTAKE.md](product/LEAD_INTAKE.md)) | **Satisfied:** agent token cannot mark gated done; schedule-at landed; cron deferred Phase 5 |
| **4** | Goals *(near done)* | Slice 1 foundation + slice 2 orchestrator stub + rails spend/time/stuck. Left: progress log / inbox / real routing | **Stub done-when met:** DoD 2 items -> >=2 sessions; cap `0.00` -> 403; stuck/wall rails |
| **5** | Triggers *(core done)* | Slices 1–3: webhook + interval automations + `lead-status-nuevo` → `lead-intake-workflow`. Optional: Ripples UI, support/bug chains ([LEAD_INTAKE.md](product/LEAD_INTAKE.md)) | **Satisfied:** secreto malo → 401; bueno → task+sesión; cron/interval test-clock; lead-status-nuevo → 2 cards |
| **6** | YAML / CLI *(core done)* | Slices 1–2: `agentos.yml` export/import + CLI create/update (+ push/pull aliases). Optional: skills/grants in YAML; goal/task/skill CLI ([AGENTOS_YML.md](agentos/AGENTOS_YML.md)) | **Satisfied:** push/CLI produce mismos agentes+template que la UI list; pull tras push identidad (whitespace aside) |
| **7** | PWA / live | Inbox PWA + push, live viewer SSE, Activity feed, routing local | Reply en móvil reanuda sesión |

Detalle corto: [agentos/PHASE2_PLUS.md](agentos/PHASE2_PLUS.md). Walkthrough completo: [agentos/POSTMA_WALKTHROUGH.md](agentos/POSTMA_WALKTHROUGH.md).

### Non-goals (no entran en esta numeración)

- Cursor Cloud Agents como runtime
- Runners solo-Mac / Electron / Tauri
- LangGraph o SaaS multi-tenant como camino del MVP

---

## Fuera de la numeración AgentOS (infra / Future)

Estas piezas **no** son Fases 3–6 del roadmap:

| Tema | Estado |
| ------ | -------- |
| **SQLite** | Ya en uso (`data/gallaia.db`) para el control plane |
| **PostgreSQL** | [ADR-003](adr/ADR-003-postgresql.md) Proposed — cuando SQLite no baste |
| **Auth de un operador** | Future (un solo operador; no multi-tenant) |
| **RAG / embeddings / chat tipo ChatGPT** | Visión larga; no el sprint actual |
| **Dominio `galladev.com`** | Solo cuando existan webhooks (Fase 5) o PWA (Fase 7) |

---

## Estructura de documentación congelada

Árbol mínimo citado por [ADR-002](adr/ADR-002-project-structure.md). Producto AgentOS y diseño viven además bajo `docs/product/`, `docs/agentos/`, `docs/design/`.

```text
docs/
├── README.md
├── ROADMAP.md                 ← este archivo (calendario AgentOS)
├── alcance.md
├── context.md
├── glossary.md
│
├── product/
│   ├── AGENTOS.md
│   ├── LEAD_INTAKE.md         ← Lead Intake (template seed Phase 3; trigger Phase 5)
│   ├── CONTROL_PLANE_NAV.md
│   └── MODULE_BOUNDARIES.md
│
├── agentos/
│   ├── README.md
│   ├── CONTRACT.md
│   ├── PHASE2_PLUS.md
│   ├── SKILLS.md              ← skills.sh (Cursor); no vendor
│   ├── AGENTOS_YML.md         ← Phase 6 agentos.yml schema
│   └── POSTMA_WALKTHROUGH.md
│
├── architecture/
│   ├── overview.md
│   ├── backend.md
│   ├── frontend.md
│   ├── database.md
│   └── api.md
│
├── backend/
│   ├── project-structure.md
│   ├── request-lifecycle.md
│   ├── configuration.md
│   ├── dependency-injection.md
│   ├── routing.md
│   ├── services.md
│   ├── repositories.md
│   ├── data-models.md
│   ├── error-handling.md
│   ├── logging.md
│   ├── testing.md
│   ├── authentication.md
│   └── glossary.md
│
├── adr/
│   ├── README.md
│   ├── ADR-001-fastapi.md
│   ├── ADR-002-project-structure.md
│   └── ADR-003-postgresql.md
│
└── assets/
    └── diagrams/
```

**No queremos una enciclopedia** — documentación útil, 2–5 páginas por deep-dive cuando aplique.

### Responsabilidad de deep-dives backend

| Documento | Responsabilidad |
| --------- | --------------- |
| `project-structure.md` | Estructura del proyecto y propósito de cada carpeta |
| `request-lifecycle.md` | Recorrido de una petición HTTP |
| `configuration.md` | Configuración (`.env`, `settings`) |
| `dependency-injection.md` | `Depends()` y dónde usarlo |
| `routing.md` | Routers y endpoints |
| `services.md` | Lógica de negocio |
| `repositories.md` | Acceso a datos |
| `data-models.md` | Modelos ORM y esquemas Pydantic |
| `error-handling.md` | Errores y excepciones |
| `logging.md` | Estrategia de logs |
| `testing.md` | Organización de pruebas |

Índice completo: [docs/README.md](README.md).
