# Phase 1 — Gaps conocidos

Documento de análisis de gaps identificados en la Phase 1 (AgentOS MVP) de GallaAI. Generado a partir de una revisión profunda del código fuente, rutas API, frontend y tests.

**Fecha de análisis:** 9 septiembre 2026
**Rama de referencia:** `feat/agentos-mvp` / `master`

> Este documento **no** bloquea el avance a Phase 2. Phase 1 es funcional como MVP de aprendizaje. Los gaps listados son conocidos y aceptados para la fase actual.

---

## Resumen ejecutivo

| Severidad | Cantidad | Descripción |
|-----------|----------|-------------|
| **Crítico** | 6 | Gaps que afectan la integridad del sistema o dejan features core sin uso |
| **Menor** | 12 | Nice-to-have, aceptables para MVP de aprendizaje |
| **Total** | **18** | |

La causa raíz de la mayoría de los gaps críticos es la existencia de **dos sistemas paralelos** (SQLAlchemy control plane + AgentOS in-memory) que evolucionaron de forma independiente. El frontend solo consume el sistema AgentOS (in-memory), dejando la capa SQL sin uso visible.

---

## Gaps críticos (C1–C6)

### C1 — Frontend solo usa endpoints AgentOS (in-memory)

**Archivo:** `frontend/src/api/client.ts` (todo el archivo)
**Ubicación:** Todos los métodos del cliente API apuntan a `/api/v1/agentos/*`

**Descripción:**
El frontend consume exclusivamente los endpoints del paquete AgentOS in-memory (`/api/v1/agentos/agents`, `/tasks`, `/sessions`, `/inbox`). Los endpoints SQL del control plane (`/api/v1/projects`, `/agents`, `/tasks`, `/sessions`, `/inbox`) **no son consumidos** por ninguna página de la UI.

**Consecuencia:**
Toda la persistencia SQL (`backend/data/gallaia.db`) es invisible al usuario. Los datos (tasks, sessions, agents, inbox) se pierden al reiniciar el servidor. La base de datos SQLite existe pero no sirve al frontend.

**Endpoints SQL no consumidos:**
- `GET /api/v1/projects` — no hay ProjectsPage
- `GET/POST /api/v1/agents` — no consumido
- `GET/PATCH/DELETE /api/v1/tasks` — no consumido
- `POST /api/v1/tasks/{id}/run` — no consumido (usa `/api/v1/agentos/tasks/{id}/run`)
- `GET /api/v1/sessions` — no consumido
- `GET/POST /api/v1/inbox/{id}/reply` — no consumido

**Impacto:** Los criterios de éxito de Phase 1 se cumplen, pero la aplicación no tiene persistencia real. Es un MVP funcional pero efímero.

---

### C2 — Dos sistemas de runner con comportamiento divergente

**Archivos:**
- `backend/app/agentos/runner.py` (in-memory, usado por UI)
- `backend/app/services/runner.py` (SQL, no usado por UI)

**Descripción:**
Existen dos implementaciones de runner completamente separadas:

| Característica | `agentos/runner.py` | `services/runner.py` |
|----------------|---------------------|----------------------|
| Persistencia | In-memory (dict) | SQLAlchemy (SQLite) |
| Approval gate | **Ignorado** — auto-cierra a `done` | **Respeta** — deja en `review` |
| Inbox messages | No crea | Crea `InboxMessage` cuando gate activo |
| Tool events | `ToolEvent` dataclass | JSON en campo `tool_call_log` |
| Schema de eventos | `{ name, input, output, at }` | `{ ts, tool, detail }` |
| Runner resolution | `resolve_runner()` | `_control_plane_runner()` |

**Consecuencia:**
- El runner que usa la UI (`agentos/runner.py`) **siempre auto-cierra** las tasks, ignorando approval gates.
- El runner que respeta gates (`services/runner.py`) es inalcanzable desde la UI.
- Los formatos de tool events son incompatibles entre sí.

**Impacto:** El flujo approval gate está roto. El runner SQL tiene funcionalidad que nunca se ejecuta.

---

### C3 — Approval gate sin UI funcional

**Archivos:**
- `frontend/src/pages/TasksPage.tsx:163-208` (formulario de creación)
- `frontend/src/pages/TasksPage.tsx:216-259` (tablero Kanban)

**Descripción:**
El approval gate es una feature core de Phase 1 (documentada en `docs/agentos/POSTMA_WALKTHROUGH.md:153` y `docs/agentos/PHASE2_PLUS.md:25`), pero la UI no lo soporta:

1. **Sin toggle al crear task:** El formulario de creación (`TasksPage.tsx:163-208`) no tiene checkbox/campo para `approval_gate`.
2. **Sin distinción visual:** La columna "review" del Kanban no se diferencia visualmente de "done". No hay indicadores de que una task requiere aprobación humana.
3. **Sin acciones approve/reject:** No hay botones para aprobar o rechazar tasks en "review".
4. **"Ejecutar ahora" disponible en review:** El botón Run se oculta solo para `col === 'done'` (linea 243), permitiendo re-ejecutar tasks que están en review.

**Consecuencia:** Los usuarios no pueden usar approval gates desde la UI. La feature solo es accesible vía API directa (setting `approval_gate: true` en el POST body).

**Impacto:** Feature documentada como core de Phase 1 está completamente muerta en la UI.

---

### C4 — Inbox desconectado y ephemeral

**Archivos:**
- `backend/app/api/routes/inbox.py` (SQL inbox)
- `backend/app/api/routes/agentos.py:147-183` (AgentOS inbox)
- `frontend/src/pages/InboxPage.tsx:32`

**Descripción:**
Hay dos sistemas de inbox completamente separados:

**Sistema A — SQL Inbox (`InboxMessage`):**
- Modelo: `backend/app/models/inbox.py`
- Creado por `services/runner.py:118-127` cuando `approval_gate=True`
- Persiste en SQLite
- **Nunca se muestra en la UI** (el frontend no consume `/api/v1/inbox`)

**Sistema B — AgentOS Inbox (in-memory):**
- Computado al vuelo en `agentos.py:147-183`
- Recopila sesiones `waiting-inbox` y tasks `review`
- **Ephemeral** — se pierde al reiniciar servidor
- **Es lo que muestra la UI** (`InboxPage.tsx:32` llama `api.inbox()` → `/api/v1/agentos/inbox`)

**Consecuencia:**
- Los inbox messages reales (SQL) son invisibles
- Los inbox items visibles (AgentOS) son ephemeral
- El reply endpoint (`POST /inbox/{id}/reply`) es un stub que no reanuda sesiones
- Los acknowledge/snooze en la UI son estado local (se pierden al refrescar)

**Impacto:** No hay inbox persistente y funcional. El canal de interrupción humana está roto.

---

### C5 — Cero tests de rutas API

**Archivos:**
- `backend/tests/test_agentos_runner.py` (único archivo de tests, 157 líneas)

**Descripción:**
Todos los tests existentes cubren **solo** el módulo AgentOS in-memory (seeds + runner mock). No existe ningún test que valide:

- Rutas HTTP (no hay uso de `fastapi.testclient.TestClient`)
- Modelos SQLAlchemy ni operaciones CRUD
- Schemas Pydantic
- El runner SQL (`services/runner.py`)
- Lógica de inbox
- Manejo de errores
- Seed service (`services/seed.py`)

**Consecuencia:** No hay seguridad de regresión para ningún endpoint. Cualquier cambio puede romper funcionalidad sin ser detectado.

**Impacto:** Riesgo de regresiones silenciosas. No se puede validar el contrato HTTP de la API.

---

### C6 — Seeds duplicados con configuración divergente

**Archivos:**
- `backend/app/services/seed.py` (seeds SQL)
- `backend/app/agentos/seeds.py` (seeds AgentOS)

**Descripción:**
Los dos sistemas de seeds crean agentes con nombres iguales pero configuración diferente:

| Campo | SQL (`seed.py`) | AgentOS (`seeds.py`) |
|-------|-----------------|----------------------|
| Modelos | `claude-sonnet-4`, `claude-opus-4`, `claude-sonnet-4` | `claude-sonnet-4-5` (todos) |
| Runner pref | `cloud`, `cloud`, `local` | `inherit`, `anthropic`, `mock` |
| Skills | No tiene | `plan-mode`, `code`, `review` |
| MCP | No tiene | `agentos`, `inbox` |
| one_job | No tiene | Sí (descripción del rol) |

**Consecuencia:** Los agentes se comportan diferente dependiendo de qué sistema se use. El modelo `claude-opus-4` en SQL no existe en AgentOS. Los runner preferences `cloud`/`local` no son reconocidos por `resolve_runner()`.

**Impacto:** Configuración inconsistente entre los dos subsistemas.

---

## Gaps menores (N1–N12)

| # | Gap | Ubicación | Notas |
|---|-----|-----------|-------|
| N1 | No hay Projects page en frontend | No existe `ProjectsPage.tsx` | Aceptable con proyecto default único |
| N2 | Agent status siempre "healthy" | `AgentsPage.tsx:14-17` | Sin sistema de heartbeat |
| N3 | No task deletion desde UI | `TasksPage.tsx` | Minor |
| N4 | Inbox reply es stub | `inbox.py:32-33` | Documentado como Phase 1 limitation |
| N5 | No frontend tests | `frontend/` sin archivos `*.test.*` | Común para MVP |
| N6 | No React ErrorBoundary | `frontend/src/` | Errores de render crashean la app |
| N7 | No retry logic en API client | `client.ts:77-100` | Errores transitorios requieren refresh |
| N8 | No sample seed data (tasks, inbox) | Ambos seed files | Kanban e inbox vacíos al inicio |
| N9 | Docker build requiere frontend pre-build en host | `Dockerfile` | Documentado en comentario |
| N10 | No dev-mode Docker | `Dockerfile` | Solo producción con uvicorn |
| N11 | Tool events solo muestran output | `SessionsPage.tsx:83` | Input no visible |
| N12 | No real-time session polling | `SessionsPage.tsx:18-46` | Aceptable para sessions rápidas (mock) |

---

## Non-goals confirmados (fuera de alcance por diseño)

Estos items **no** son gaps — están documentados como excluidos de Phase 1:

- Auth multi-usuario / multi-tenant
- PostgreSQL obligatorio (ADR-003 es Proposed)
- Agent SDK / Managed Agents completo (solo stub Messages)
- Isolation ACL / red / filesystem (Phase 2+)
- Templates con gates (Phase 3)
- Goals + orquestador (Phase 4)
- Triggers / webhooks (Phase 5)
- YAML / CLI (Phase 6)
- PWA / live SSE (Phase 7)
- Cursor Cloud Agents como runtime
- Runners solo-Mac / Electron / Tauri

---

## Relación con criterios de éxito

Los criterios de éxito de Phase 1 (`docs/alcance.md:65-71`) se cumplen **técnica pero no plenamente**:

| Criterio | Estado | Detalle |
|----------|--------|---------|
| Abrir aplicación (local/Docker) | ✅ | Funcional |
| Ver agentes seed / crear task | ✅ | Funcional (AgentOS in-memory) |
| Lanzar Ejecutar ahora | ✅ | Funcional (mock/stub) |
| Ver session con tool log | ✅ | Funcional (AgentOS) |
| Ver items en Inbox | ⚠️ | Funcional pero ephemeral |

El MVP es **usable para aprendizaje** pero no tiene persistencia real ni approval gates funcionales.

---

## Recomendaciones

### Para cerrar Phase 1 completamente

1. **Unificar runners:** Decidir un solo runner (SQL o in-memory) y eliminar el otro. Probablemente SQL para persistencia.
2. **Conectar frontend a SQL:** Actualizar `api/client.ts` para consumir endpoints SQL.
3. **Approval gate UI:** Agregar toggle en formulario + acciones approve/reject en Kanban.
4. **Inbox persistente:** Conectar frontend a SQL inbox + implementar reply funcional.
5. **Tests API:** Agregar tests con `TestClient` para las rutas principales.

### Para avanzar a Phase 2

Los gaps de Phase 1 **no bloquean** Phase 2 (Isolation), ya que Phase 2 es un tema diferente (ACL, grants, filesystem MCP). Sin embargo, cerrar C1–C4 antes de Phase 2 daría una base más sólida.

---

## Documentos relacionados

- [docs/ROADMAP.md](ROADMAP.md) — Calendario de fases
- [docs/alcance.md](alcance.md) — Alcance y criterios de éxito
- [docs/agentos/PHASE2_PLUS.md](agentos/PHASE2_PLUS.md) — Sketch de fases futuras
- [docs/agentos/POSTMA_WALKTHROUGH.md](agentos/POSTMA_WALKTHROUGH.md) — Referencia del blueprint original
- [docs/product/AGENTOS.md](product/AGENTOS.md) — Mapa de producto
- [memory-bank/progress.md](../memory-bank/progress.md) — Registro de progreso
