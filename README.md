# GallaIA — AgentOS control plane

Plataforma de aprendizaje + **AgentOS MVP**: control plane web (Kanban, sesiones, inbox), inspirado en el talk de Danny Postma, con **FastAPI + React + Lucide**.

| | |
| --- | --- |
| **Branch** | `feat/agentos-mvp` (desde `master`) |
| **Plataformas** | Windows / Linux / macOS — navegador + API |
| **UI** | Atelier (cream / indigo / coral). No es el tema Linear de Leads_CRM. |
| **Runtime default** | Mock. Opcional OpenRouter (Nemotron) o Anthropic Messages stub. |

**No** Electron, Tauri ni exclusividad Mac. **No** Cursor Cloud Agents como runtime de este MVP.

## Docs

- Roadmap (fases 0–7): [docs/ROADMAP.md](docs/ROADMAP.md)
- Mapa: [docs/product/AGENTOS.md](docs/product/AGENTOS.md)
- Sidebar (doc only): [docs/product/CONTROL_PLANE_NAV.md](docs/product/CONTROL_PLANE_NAV.md)
- Modulos: [docs/product/MODULE_BOUNDARIES.md](docs/product/MODULE_BOUNDARIES.md)
- AgentOS slice: [docs/agentos/README.md](docs/agentos/README.md)
- Walkthrough Postma: [docs/agentos/POSTMA_WALKTHROUGH.md](docs/agentos/POSTMA_WALKTHROUGH.md)
- Phase 2+: [docs/agentos/PHASE2_PLUS.md](docs/agentos/PHASE2_PLUS.md)
- Backend: [backend/README.md](backend/README.md)
- Frontend: [frontend/README.md](frontend/README.md)
- Docker (UI+API un contenedor): [docs/deployment/docker.md](docs/deployment/docker.md) · [docker-compose.md](docs/deployment/docker-compose.md)

## Vision

Defines agentes, creas tareas y lanzas **Ejecutar ahora**. Cada run genera una **Session** con tool-call log y avanza el Kanban (todo / doing / review / done). El **Inbox** concentra decisiones humanas.

Modelo: **Project · Agent · Task · Session · Inbox**.

Seeds: `default`, `plan`, `senior-dev`. Prompts en `backend/app/services/prompts.py` etiquetados RECONSTRUCTED (no verbatim).


## Requisitos

- Python 3.11+
- Node.js para el frontend
- SQLite (incluido; backend/data/gallaia.db)

## Arranque con Docker (recomendado)

Una imagen, un contenedor (UI + API). Desde la **raíz** del repo:

```bash
cp backend/.env.example backend/.env
# Windows: copy backend\.env.example backend\.env
npm --prefix frontend ci
npm --prefix frontend run build
docker compose up --build
```

O con el script: `bash scripts/docker-up.sh` (añade `-d` para segundo plano).

- App (UI + API): http://127.0.0.1:8000/
- OpenAPI: http://127.0.0.1:8000/docs

El build de Vite se hace en el host (npm dentro de Docker Build falla en algunos entornos Windows/proxy); el **runtime** es un solo contenedor.

Detalle: [docs/deployment/docker-compose.md](docs/deployment/docker-compose.md).

## Arranque local (sin Docker)

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

### LLM stub (opcional)

En backend/.env (nunca commitear la clave):

```env
OPENROUTER_API_KEY=
OPENROUTER_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Fallback si no usas OpenRouter:
# ANTHROPIC_API_KEY=
# ANTHROPIC_MODEL=claude-sonnet-4-5
```

Sin claves → runner mock. Con `OPENROUTER_API_KEY` → Chat Completions (UI). Anthropic Messages solo si no hay clave OpenRouter.

## Dos superficies API

1. SQLAlchemy (UI primaria): /api/v1/projects|agents|tasks|sessions|inbox → SQLite
2. In-memory AgentOS: /api/v1/agentos/* — ver docs/agentos/CONTRACT.md

Detalle: docs/product/MODULE_BOUNDARIES.md.

## Phase 2+ (no implementar en este MVP)

Isolation → Templates → Goals → Triggers → YAML/CLI → PWA: sketch en [docs/agentos/PHASE2_PLUS.md](docs/agentos/PHASE2_PLUS.md) y calendario en [docs/ROADMAP.md](docs/ROADMAP.md). Sidebar futuro (doc only): [docs/product/CONTROL_PLANE_NAV.md](docs/product/CONTROL_PLANE_NAV.md).
