# Progress

# Progress — Registro de progreso del proyecto GallaIA AgentOS

## Estado actual

Proyecto **GallaAI — AgentOS control plane** (aprendizaje + producto real). Incluye: agents, Tasks (Kanban), Sessions, Inbox, con FastAPI + React + Lucide.

- **Phase 0 — Foundation**: completada (FastAPI, Settings, logging, health, Docker/Compose, `/api/v1`, errores, middleware).
- **Phase 1 — AgentOS MVP**: completada (seeds `default`/`plan`/`senior-dev`, Kanban, sessions, inbox, runner mock + OpenRouter/Anthropic stub, UI atelier).
- **Phase 2+**: solo documentación (Isolation → Templates → Goals → Triggers → YAML/CLI → PWA). **No implementar ahora.**

Referencia de producto: `docs/product/AGENTOS.md`. Calendario: `docs/ROADMAP.md`.

## Branch actual

- `feature/phase1-gaps-docs` (nueva, documentación de gaps Phase 1)
- `feature/docs-update` (local, adelantado a origin por 3 commits)
- README/rama origen del MVP: `feat/agentos-mvp` (desde `master`)

## Log de trabajo reciente

- **PR #9** (`bcfc6ac`): feat — add OpenRouter runner: "Ejecutar ahora" puede usar Nemotron (Chat Completions OpenRouter, `backend/app/providers/openrouter.py`); la UI ya no fuerza mock.
- **PR #8** (`c4cb1e4` / `2c47441`): docs modificadas y alineadas con AgentOS.
- **PR #5** (`bc7d196`): Docker — UI + API en un solo contenedor (SQLite), Vite build en host.
- **PR #7 / #4** (`4754f56`, `93b74bd`): feat — AgentOS MVP control-plane.
- **PR #3** (`2f6bb6e`): soporte PostgreSQL + health check mejorado.
- **PR #6** (`0b06243`): merge master.

## Decisiones relevantes

- **Numeración**: Fase N = AgentOS. No usar "Fase 3" para Postgres/chat (plan antiguo cerrado).
- ADR-001 FastAPI, ADR-002 estructura de proyecto, ADR-003 PostgreSQL (Proposed — solo cuando SQLite no baste).
- Prompts de agentes son **RECONSTRUCTED** (no verbatim).
- No Electron/Tauri/Mac-only; no Cursor Cloud Agents como runtime del MVP.

## Próximas acciones

- Documentar/implementar según `docs/ROADMAP.md` (Phase 2+ solo documentada por ahora).
- Seguir con la definición de éxito de Phase 1 (crear task → Ejecutar ahora → Kanban avanza → session con tool log → Inbox).
- Postgres / auth / RAG / chat: visión larga, no el sprint actual.

## Gaps Phase 1 identificados (9 septiembre 2026)

6 gaps críticos documentados en `docs/PHASE1_GAPS.md`:

| # | Gap | Impacto |
|---|-----|---------|
| C1 | Frontend solo usa AgentOS in-memory (SQL invisible) | Sin persistencia real |
| C2 | Dos runners divergentes (in-memory vs SQL) | Approval gate roto |
| C3 | Approval gate sin UI funcional | Feature core muerta |
| C4 | Inbox desconectado (SQL invisible, AgentOS ephemeral) | Canal humano roto |
| C5 | Cero tests de rutas API | Sin regresión safety |
| C6 | Seeds duplicados con configuración divergente | Config inconsistente |

12 gaps menores (N1-N12) — nice-to-have para MVP.

**Nota:** Estos gaps **no bloquean** Phase 2 (Isolation). El MVP es funcional para aprendizaje.

## Notas / Riesgos

- `backend/.env` contiene una clave OpenRouter **real**. Está en `.gitignore` (no se commitea), pero conviene **rotarla** por higiene de seguridad.
- El proyecto prioriza el aprendizaje profundo sobre la velocidad; cada funcionalidad debe documentarse y quedar funcional antes de continuar (`docs/context.md`).
