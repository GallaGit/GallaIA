# GallaIA — AgentOS control plane

Plataforma de aprendizaje + **AgentOS MVP**: control plane web (Kanban, sesiones, inbox), inspirado en el talk de Danny Postma, con **FastAPI + React + Lucide**.

| | |
| --- | --- |
| **Branch** | `feat/agentos-mvp` (desde `master`) |
| **Plataformas** | Windows / Linux / macOS — navegador + API |
| **UI** | Atelier (cream / indigo / coral). No es el tema Linear de Leads_CRM. |
| **Runtime default** | Mock. Opcional Anthropic Messages stub. |

**No** Electron, Tauri ni exclusividad Mac. **No** Cursor Cloud Agents como runtime de este MVP.

## Docs

- Mapa: [docs/product/AGENTOS.md](docs/product/AGENTOS.md)
- Modulos: [docs/product/MODULE_BOUNDARIES.md](docs/product/MODULE_BOUNDARIES.md)
- AgentOS slice: [docs/agentos/README.md](docs/agentos/README.md)
- Phase 2+: [docs/agentos/PHASE2_PLUS.md](docs/agentos/PHASE2_PLUS.md)
- Backend: [backend/README.md](backend/README.md)
- Frontend: [frontend/README.md](frontend/README.md)

## Vision

Defines agentes, creas tareas y lanzas **Ejecutar ahora**. Cada run genera una **Session** con tool-call log y avanza el Kanban (todo / doing / review / done). El **Inbox** concentra decisiones humanas.

Modelo: **Project · Agent · Task · Session · Inbox**.

Seeds: `default`, `plan`, `senior-dev`. Prompts en `backend/app/services/prompts.py` etiquetados RECONSTRUCTED (no verbatim).


## Requisitos

- Python 3.11+
- Node.js para el frontend
- SQLite (incluido; backend/data/gallaia.db)

## Arranque local

### Backend (puerto 8000)

```bash
cd backend
python -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows PowerShell:
#   .\.venv\Scripts\Activate.ps1
# Windows Git Bash:
#   source .venv/Scripts/activate
python -m pip install -U pip
python -m pip install -e .
cp .env.example .env
# Windows: copy .env.example .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- App: http://127.0.0.1:8000/
- OpenAPI: http://127.0.0.1:8000/docs

Al arrancar: tablas SQLite + seeds default / plan / senior-dev.

### Frontend (puerto 5173)

```bash
cd frontend
npm install
npm run dev
```

UI: http://127.0.0.1:5173/ (proxy /api → FastAPI :8000).

### Claude Messages stub (opcional)

En backend/.env (nunca commitear la clave):

```env
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-5
```

Sin clave → runner mock. Con clave + runner=anthropic → stub Messages API (no Agent SDK completo).

## Dos superficies API

1. SQLAlchemy (UI primaria): /api/v1/projects|agents|tasks|sessions|inbox → SQLite
2. In-memory AgentOS: /api/v1/agentos/* — ver docs/agentos/CONTRACT.md

Detalle: docs/product/MODULE_BOUNDARIES.md.

## Phase 2+ (no implementar en este MVP)

Isolation/ACL, R2, goals, triggers, YAML CLI: solo sketch en docs/agentos/PHASE2_PLUS.md.
