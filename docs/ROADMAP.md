# Roadmap — GallaIA AgentOS

**Fuente de verdad del calendario de producto.** Numeración **Fase N = AgentOS**. No usar “Fase 3” para Postgres, chat u otros planes antiguos.

Mapa de producto Phase 1: [product/AGENTOS.md](product/AGENTOS.md).  
Orden de réplica Postma: [agentos/POSTMA_WALKTHROUGH.md](agentos/POSTMA_WALKTHROUGH.md) §4.  
Sketch post-MVP: [agentos/PHASE2_PLUS.md](agentos/PHASE2_PLUS.md).  
Sidebar (doc only): [product/CONTROL_PLANE_NAV.md](product/CONTROL_PLANE_NAV.md).  
Contrato API MVP: [agentos/CONTRACT.md](agentos/CONTRACT.md).

> El plan antiguo Foundation → Postgres → auth → users → **chat** está **cerrado**. No decidir sprints con esa lista.

---

## Fases AgentOS

### Hecho

| Fase | Nombre | Qué incluye | Done when |
|------|--------|-------------|-----------|
| **0** | Foundation | FastAPI, Settings, logging, health, Docker / Compose, `/api/v1`, errores, middleware | App abre, health ok |
| **1** | AgentOS MVP | Seeds `default` / `plan` / `senior-dev`, Kanban, sessions, inbox, mock runner, stub Anthropic Messages, UI atelier | Crear task → run → Kanban avanza → session con tool log |

Detalle Phase 1: [product/AGENTOS.md](product/AGENTOS.md).

### Siguiente (solo documentación — no implementar ahora)

| Fase | Nombre | Qué incluye | Done when (cuando se implemente) |
| ------ | -------- | ------------- | ---------------------------------- |
| **2** | Isolation | Grants MCP/repo/env (default deny), network `open`\|`limited`, filesystem MCP + ACL, secret refs | Agente support con Front fake no llama GitHub ni lee carpeta ajena |
| **3** | Templates | `TaskTemplate` + instantiate, approval gates en API/MCP, cadena `compound-engineer-workflow`, schedule | Instantiate → 9 cards; paso 2 no arranca hasta humano marca 1 `done` |
| **4** | Goals | DoD aprobado, orquestador, rails spend/time/stuck | DoD 2 ítems → ≥2 sesiones; cap `0.00` rechaza spawn |
| **5** | Triggers | Webhooks firmados, automations cron, seeds support/bug | Secreto malo → 401; bueno → task+sesión |
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
│   ├── CONTROL_PLANE_NAV.md
│   └── MODULE_BOUNDARIES.md
│
├── agentos/
│   ├── README.md
│   ├── CONTRACT.md
│   ├── PHASE2_PLUS.md
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
