# Tech Context

# Tech Context — Contexto técnico del proyecto GallaIA AgentOS

## Descripción

**GallaAI** es una plataforma de aprendizaje + **AgentOS control plane** (web: Kanban, sesiones, inbox), inspirada en el talk de Danny Postma. Modelo de dominio: **Project · Agent · Task · Session · Inbox**. UI "Atelier" (cream / indigo / coral).

## Stack

| Capa | Tecnología |
| ---- | ---------- |
| Backend | FastAPI (Python 3.11+, `gallaai-backend` v0.2.0), SQLAlchemy 2.0, pydantic-settings |
| Base de datos | SQLite (`backend/data/gallaia.db`) — control plane. Postgres futuro (ADR-003, Proposed) |
| Frontend | React 19 + TypeScript 5.8 + Vite 6 + react-router-dom 7 + lucide-react (`gallaia-agentos-frontend` v0.2.0) |
| Docker | Una imagen + un contenedor (UI + API) en `:8000`. Vite build en host (npm dentro de Docker falla en algunos Windows/proxy) |

## Estructura de carpetas clave

- `backend/app/` — aplicación FastAPI
  - `api/routes/` — agentos, agents, health, inbox, projects, sessions, tasks
  - `agentos/` — paquete AgentOS in-memory (models.py, runner.py, seeds.py, store.py, schemas.py)
  - `core/` — config (Settings), logging
  - `providers/openrouter.py` — adaptador Chat Completions
  - `services/` — prompts (RECONSTRUCTED), runner, seed
  - `db/`, `models/`, `schemas/`, `middleware/`, `exceptions/`
- `frontend/src/` — `App.tsx`, `api/client.ts`, `pages/`, `styles/atelier.css`
- `docs/` — documentación (ROADMAP, product/, agentos/, architecture/, adr/, backend/)
- `scripts/docker-up.sh` — script de arranque Docker

## Dos superficies API

1. **SQLAlchemy (UI primaria)**: `/api/v1/projects|agents|tasks|sessions|inbox` → SQLite
2. **AgentOS in-memory**: `/api/v1/agentos/*` — ver `docs/agentos/CONTRACT.md`

## Configuración

- `backend/.env` (nunca commitear claves), plantilla `backend/.env.example`
- Claves LLM opcionales vía `OPENROUTER_API_KEY` / `ANTHROPIC_API_KEY`. Claves vacías → runner **mock**
- Modelo OpenRouter por defecto: `nvidia/nemotron-3-ultra-550b-a55b:free`
- Settings en `backend/app/core/config.py` (pydantic-settings, `get_settings()` cacheada)

## Runners de sesión

`backend/app/agentos/runner.py` — avanzan task por Kanban y registran tool-events:
- `mock` (por defecto sin claves)
- `openrouter` (Chat Completions, cuando existe key)
- `anthropic` (solo si se pide y hay key)
- Fallback a mock si la llamada falla; errores se registran como tool-events

## Modelo de dominio / Seeds

- Seeds: `default`, `plan`, `senior-dev` — en `backend/app/agentos/seeds.py`
- Prompts en `backend/app/services/prompts.py` etiquetados **RECONSTRUCTED** (no verbatim)
- Kanban: todo → doing → review → done (MVP auto-cierra; approval gates en Phase 3)

## Convenciones

- Documentación en `docs/` (roadmap congelado, en español)
- **No** usar "Fase 3" para Postgres/chat: numeración **Fase N = AgentOS** (ver `docs/ROADMAP.md`)
- Phase 2+ (Isolation→Templates→Goals→Triggers→YAML/CLI→PWA) se **documenta** antes de implementarse (`docs/agentos/PHASE2_PLUS.md`)
- No Electron / Tauri / exclusividad Mac; no Cursor Cloud Agents como runtime del MVP

## Arranque

- **Docker (recomendado)**: desde la raíz, `docker compose up --build` → http://127.0.0.1:8000/ (OpenAPI `/docs`)
- **Local**: backend `uvicorn app.main:app :8000`, frontend `npm run dev` → http://127.0.0.1:5173/ (proxy `/api` → 8000)
- Decisiones clave: ADR-001 FastAPI, ADR-002 estructura, ADR-003 PostgreSQL (Proposed)
