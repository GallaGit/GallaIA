# GallaIA AgentOS — mapa de producto (Phase 0 + Phase 1)

Documento de producto del **control plane** AgentOS en GallaIA. Inspirado en el talk de Danny Postma (*How I Built My Own AgentOS on Claude's Agent SDK*), adaptado a un stack web multiplataforma.

> **Estado local:** draft en `feat/agentos-mvp` @ `61ba264` (push remoto pendiente).

| Estado | Alcance |
|--------|---------|
| **Confirmado (Phase 1 MVP)** | Seeds, Kanban, sesiones, inbox, mock runner, stub Anthropic Messages |
| **Solo documentación (Phase 2+)** | Isolation/ACL, R2, goals, triggers, YAML CLI — ver [PHASE2_PLUS.md](../agentos/PHASE2_PLUS.md) |

> **No es Mac-only.** No Electron, Tauri ni exclusividad de SO. Corre en **Windows / Linux / macOS** vía navegador + API.
> **UI:** atelier propio (React + Lucide; paleta cream / indigo / coral). **No** reutiliza el tema Linear de Leads_CRM.

Límites de módulo y dos superficies API: [MODULE_BOUNDARIES.md](MODULE_BOUNDARIES.md).

---

## Visión (confirmado)

AgentOS es el **plano de control** donde defines agentes, creas tareas en un tablero Kanban y lanzas ejecuciones ("Ejecutar ahora"). Cada run produce una **Session** con log de tool-calls; el **Inbox** canaliza interrupciones humanas (decisiones, bloqueos, gates de aprobación).

El runtime por defecto es **mock**. Con `ANTHROPIC_API_KEY` opcional se puede usar un **stub** de la Messages API (no es el Agent SDK completo ni Cursor Cloud Agents).

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

Frontend React + Vite + TypeScript + Lucide. Estética **atelier**: cream / indigo / coral. Páginas de projects, agents, tasks (Kanban), sessions e inbox consumen las rutas SQLAlchemy vía `frontend/src/api/client.ts`.

---

## Phase 2+ — solo documentación (no implementar en este MVP)

Sketch en [docs/agentos/PHASE2_PLUS.md](../agentos/PHASE2_PLUS.md). Incluye, entre otros:

| Tema | Notas |
|------|--------|
| Isolation / ACL | Grants MCP/repo/env; least privilege |
| R2 / Files | Placeholder docs; MCP filesystem real más tarde |
| Goals | Gauntlet / DoD / orchestrator |
| Triggers | Webhooks firmados → task + session |
| YAML CLI | Fuera de scope Phase 1 |

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
| Goals / triggers / YAML CLI | Fuera de scope | Ver PHASE2_PLUS |

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
| Docs | Este mapa, MODULE_BOUNDARIES, agentos CONTRACT / PHASE2_PLUS |

Arranque local: ver [README.md](../../README.md) (venv + uvicorn `:8000`, Vite `:5173`).
