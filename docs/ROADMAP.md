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
- Gate "token de agente no puede PATCH done" en paso gated (auth/actor).
- UI Templates / Skills.
- Phase 3 close criteria: agent token no marca gated `done`; schedule/cron aterrizado o explícitamente deferred.


### Slice Phase 3.5 — schedule-at on tasks (este PR)

**Hecho**

- Campo Task.scheduled_at (datetime opcional, indexado) + ALTER lean en init_db para SQLite existente.
- API PATCH /api/v1/tasks/{id}/schedule para set/clear; TaskOut expone scheduled_at.
- Demo tick POST /api/v1/scheduler/tick (body opcional 
ow para test clock): promueve due (scheduled_at <= now), limpia schedule, crea session stub 
unner=scheduler / status=queued si hay assignee.
- Pytest: future no due; past promovido + stub; clear; sin assignee sin session. Cron string runner **deferred** a Phase 5 (test skipped documentado).

**Por hacer (siguientes slices Phase 3 — no este PR)**

- Assignee agents for compound steps (roles seed faltantes: spec, 
eview-coordinator, etc.).
- Gate "token de agente no puede PATCH done" en paso gated (auth/actor).
- UI Templates / Skills.
- Phase 3 close criteria: agent token no marca gated done; cron recurrencia plena = Phase 5 (schedule-at aterrizado aquí).


---


---

## Fases AgentOS

### Hecho

| Fase | Nombre | Qué incluye | Done when |
|------|--------|-------------|-----------|
| **0** | Foundation | FastAPI, Settings, logging, health, Docker / Compose, `/api/v1`, errores, middleware | App abre, health ok |
| **1** | AgentOS MVP | Seeds `default` / `plan` / `senior-dev`, Kanban, sessions, inbox, mock runner, stub Anthropic Messages, UI atelier | Crear task → run → Kanban avanza → session con tool log |
| **2** | Isolation | Grants MCP/repo/env (default deny), network `open`\|`limited`, filesystem MCP + ACL, secret refs | Support Front-only no llama GitHub ni fetch fuera de allowlist ni lee carpeta ajena; secret refs sin plaintext en DB |

Detalle Phase 1: [product/AGENTOS.md](product/AGENTOS.md). Isolation: [PHASE2_PLUS.md](agentos/PHASE2_PLUS.md) §Phase 2.

### Siguiente

**En curso: Fase 3 Templates** (slice 5: schedule-at). Isolation (Phase 2) está **done**. UI Files/Connections queda como follow-up. Resto de Phase 3–7: sketch / siguientes slices.

| Fase | Nombre | Qué incluye | Done when (cuando se implemente) |
| ------ | -------- | ------------- | ---------------------------------- |
| **3** | Templates *(en curso)* | Slice 1–3 done (templates + Skills). Slice 4: seed `lead-intake-workflow` + agents. Luego: schedule/cron; compound assignee agents ([LEAD_INTAKE.md](product/LEAD_INTAKE.md)) | Lead-intake: 2 cards + gate. Full Phase 3: agent token no marca gated `done` + schedule/cron o deferred |
| **4** | Goals | DoD aprobado, orquestador, rails spend/time/stuck | DoD 2 ítems → ≥2 sesiones; cap `0.00` rechaza spawn |
| **5** | Triggers | Webhooks firmados, automations cron, seeds support/bug; seed doc `lead-status-nuevo` ([LEAD_INTAKE.md](product/LEAD_INTAKE.md)) | Secreto malo → 401; bueno → task+sesión |
| **6** | YAML / CLI | `agentos.yml` push/pull, CLI create/update | Push produce mismos agentes+template que la UI |
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
