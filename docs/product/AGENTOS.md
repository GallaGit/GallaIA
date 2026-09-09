# GallaIA AgentOS — mapa de producto (Phase 0 + Phase 1)

Documento de producto del **control plane** AgentOS en GallaIA. Inspirado en el talk de Danny Postma (*How I Built My Own AgentOS on Claude's Agent SDK*), adaptado a un stack web multiplataforma.

> **Estado:** en `feat/agentos-mvp` @ `6800d54` / [PR #4](https://github.com/GallaGit/GallaIA/pull/4). Telemetria Fase 1 sigue como propuesto/pendiente.

| Estado | Alcance |
|--------|---------|
| **Confirmado (Phase 1 MVP)** | Seeds, Kanban, sesiones, inbox, mock runner, stub Anthropic Messages |
| **Solo documentación (Phase 2+)** | Isolation → Templates → Goals → Triggers → YAML → PWA — ver [PHASE2_PLUS.md](../agentos/PHASE2_PLUS.md), [ROADMAP.md](../ROADMAP.md) |
| **Sidebar futuro (doc only)** | Activity, Goals, Skills, Environment, Templates, Knowledge, Ripples, Connections, Admin — [CONTROL_PLANE_NAV.md](CONTROL_PLANE_NAV.md) |

> **No es Mac-only.** No Electron, Tauri ni exclusividad de SO. Corre en **Windows / Linux / macOS** vía navegador + API.
> **UI:** atelier propio (React + Lucide; paleta cream / indigo / coral). **No** reutiliza el tema Linear de Leads_CRM.

Límites de módulo y dos superficies API: [MODULE_BOUNDARIES.md](MODULE_BOUNDARIES.md).

Qué enseñó Postma en el video y el orden de réplica: [POSTMA_WALKTHROUGH.md](../agentos/POSTMA_WALKTHROUGH.md).

---

## Visión (confirmado)

AgentOS es el **plano de control** donde defines agentes, creas tareas en un tablero Kanban y lanzas ejecuciones ("Ejecutar ahora"). Cada run produce una **Session** con log de tool-calls; el **Inbox** canaliza interrupciones humanas (decisiones, bloqueos, gates de aprobación).

El runtime por defecto es **mock**. Con `OPENROUTER_API_KEY` se usa un stub de Chat Completions (Nemotron vía OpenRouter). Con `ANTHROPIC_API_KEY` (y sin OpenRouter en la UI) se usa un stub de Messages API. Ninguno es el Agent SDK completo ni Cursor Cloud Agents.

---

## Modelo mental

| Concepto | Rol |
|----------|-----|
| **Project** | Workspace / contenedor de trabajo |
| **Agent** | Rol + prompts fundacionales y de rol |
| **Task** | Unidad de trabajo en Kanban: `todo` \| `doing` \| `review` \| `done` |
| **Session** | Registro de una ejecución + log de tool-calls |
| **Inbox** | Canal de interrupción / decisión humana |

Flujo típico Phase 1: crear task → asignar agente → run → status avanza (`todo` → `doing` → …) → eventos en session → opcionalmente inbox si hace falta humano.

---

## Phase 1 — MVP (confirmado)

### Seeds de agentes

Al arrancar (o vía seeds), el sistema registra al menos:

- `default` — agente genérico
- `plan` — convierte especificación aprobada en plan de implementación (no implementa)
- `senior-dev` — implementa / aplica fixes en el repo concedido

### Prompts — RECONSTRUCTED (no verbatim)

Todos los prompts del MVP están en `backend/app/services/prompts.py`.

**Importante:** son **reconstruidos** a partir del talk de Danny Postma — **no** son sus archivos de prompt literales. Cada seed / string debe llevar la etiqueta de procedencia (label required). No se debe tratar el texto como copyright del autor del talk.

### Runtime

| Modo | Condición | Comportamiento |
|------|-----------|----------------|
| **Mock** (default) | Sin clave o runner mock | Avanza Kanban y appendea tool-event log |
| **OpenRouter stub** | `OPENROUTER_API_KEY` | Chat Completions (modelo default Nemotron free) |
| **Anthropic stub** | `ANTHROPIC_API_KEY` + runner anthropic | Llamada Messages API (stub); no Agent SDK completo |

### Superficies API (ambas montadas)

Ver detalle y ownership en [MODULE_BOUNDARIES.md](MODULE_BOUNDARIES.md).

1. **SQLAlchemy control plane** (frontend primario)
   - Rutas: `/api/v1/projects` \| `agents` \| `tasks` \| `sessions` \| `inbox`
   - Persistencia: SQLite (`data/gallaia.db`)

2. **In-memory AgentOS package** (contrato Backend teammate)
   - Rutas: `/api/v1/agentos/*`
   - Store en memoria de proceso; contrato en [docs/agentos/CONTRACT.md](../agentos/CONTRACT.md)
   - Overview MVP: [docs/agentos/README.md](../agentos/README.md)

No eliminar ninguna superficie sin coordinación. Convergencia de runners → más adelante, detrás de una interfaz de servicio común.

### UI (atelier)

Frontend React + Vite + TypeScript + Lucide. Estética **atelier**: cream / indigo / coral. Páginas de agents, tasks (Kanban), sessions e inbox consumen las rutas SQLAlchemy vía `frontend/src/api/client.ts`.

### Sidebar (implementado vs doc-only)

| Nav | Estado |
|-----|--------|
| Agents, Tasks, Sessions, Inbox | Implementado (Phase 1) |
| Files, Settings | Placeholder EmptyState |
| Activity, Goals, Skills, Environment, Templates, Knowledge, Ripples, Connections, Admin | **Solo documentación** — [CONTROL_PLANE_NAV.md](CONTROL_PLANE_NAV.md) |

---

## Phase 2+ — solo documentación (no implementar en este MVP)

Sketch en [docs/agentos/PHASE2_PLUS.md](../agentos/PHASE2_PLUS.md) (numeración = [ROADMAP.md](../ROADMAP.md)). Incluye, entre otros:

| Fase | Tema | Notas |
|------|------|--------|
| 2 | Isolation / ACL | Grants MCP/repo/env; Environment + Connections + Files reales |
| 3 | Templates + gates | Cadena 9 pasos; Skills CRUD mínimo; seed doc `lead-intake-workflow` |
| 4 | Goals | Gauntlet / DoD / orchestrator |
| 5 | Triggers | Webhooks firmados → task + session; Ripples; seed doc `lead-status-nuevo` |
| 6–7 | YAML CLI / PWA | Admin sync; Activity feed + live viewer |

Workflow comercial Planned (doc only): [LEAD_INTAKE.md](LEAD_INTAKE.md).

**Non-goals actuales:** Cursor Cloud Agents como runtime; runners solo-Mac; LangGraph / multi-tenant SaaS como camino del MVP.

---

## Confirmado vs later (resumen)

| Feature | Phase 1 (confirmado) | Later (doc only / Phase 2+) |
|---------|----------------------|-----------------------------|
| Agents + prompts | Seeds `default` / `plan` / `senior-dev`; prompts RECONSTRUCTED | ACL, skills, MCPs ricos |
| Kanban + run now | Mock / Claude Messages stub | Schedule, templates, chains |
| Session tool log | Eventos persistidos (SQL) / in-memory (agentos) | Live SSE + Agent SDK |
| Inbox | List + reply stub | Resume session, PWA push |
| Isolation / R2 | Docs + placeholder Files | ACL real + R2 MCP |
| Goals / templates / triggers / YAML CLI | Fuera de scope | Ver PHASE2_PLUS + CONTROL_PLANE_NAV |
| Lead Intake (CRM `nuevo` → 2 agents + score) | Fuera de scope | Doc only — [LEAD_INTAKE.md](LEAD_INTAKE.md) |
| Activity / Ripples / Knowledge / Admin | Fuera de scope | Doc only — CONTROL_PLANE_NAV |

---

## Telemetría Fase 1 (propuesto / pendiente de instrumentar)

**Estado:** propuesto por Data Analyst; pendiente de instrumentar. **No** es hecho ni parte del MVP implementado.

Lista mínima (7 items):

| Evento / métrica | Notas |
| --- | --- |
| `session_started` / `session_ended` | Ciclo de vida de sesión |
| `session_duration_ms` | Duración de la sesión |
| `task_created` | Alta de tarea |
| `task_status_changed` | Cambio en Kanban |
| `tasks_by_status` | Conteo por estado |
| `mock_run_started` / `mock_run_completed` | Runner mock |
| `mock_run_duration_ms` | Duración del run mock |

**Fuera de Fase 1** (no son trabajo Phase 1 de esta lista): tokens LLM, latencia de proveedor, ROI/conversión, multi-agente.

## Ownership

| Capa | Responsabilidad |
|------|-----------------|
| Backend | Persistencia SQLAlchemy, seeds, runner mock/stub, rutas `/api/v1/*` y `/api/v1/agentos/*` |
| Frontend | Atelier UI, Kanban, cliente HTTP hacia control plane SQLAlchemy |
| Docs | Este mapa, MODULE_BOUNDARIES, CONTROL_PLANE_NAV, agentos CONTRACT / PHASE2_PLUS / ROADMAP |

Arranque local: ver [README.md](../../README.md) (venv + uvicorn `:8000`, Vite `:5173`).
