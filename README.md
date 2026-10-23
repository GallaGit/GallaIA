# GallaIA v2 — equipo agéntico personal

Herramienta personal para que **Ociel** construya software con tres agentes que se coordinan:

| Agente | Rol |
|--------|-----|
| **Orquestador** | Habla con el usuario, planifica, divide, delega a FE/BE, revisa e integra |
| **FE** | React / TypeScript / UI |
| **BE** | FastAPI / API / datos |

Stack actual: **FastAPI + SQLAlchemy/SQLite** (backend) y **React + Vite** (frontend). Runtime mock por defecto; gateway LLM con OpenRouter como proveedor principal y Groq de respaldo (`litellm` opcional). LangGraph / MCP llegan en F2+.

| | |
| --- | --- |
| **Branch base** | `master` |
| **UI** | Atelier (cream / indigo / coral) |
| **Agentes seed** | `orquestador`, `fe`, `be` |

## Docs

- Visión: [docs/VISION.md](docs/VISION.md)
- Arquitectura (6 capas): [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md)
- Roadmap F0–F5: [docs/ROADMAP.md](docs/ROADMAP.md)
- Índice: [docs/README.md](docs/README.md)
- Archivo v1 (AgentOS): [docs/archive/README.md](docs/archive/README.md)
- Backend: [backend/README.md](backend/README.md)
- Frontend: [frontend/README.md](frontend/README.md)
- Docker: [docs/deployment/docker.md](docs/deployment/docker.md)

## Requisitos

- Python 3.11+
- Node.js para el frontend
- SQLite (`backend/data/gallaia.db`)

## Arranque con Docker (recomendado)

```bash
cp backend/.env.example backend/.env
# Obligatorio: rellena GALLAIA_OPERATOR_TOKEN (>=32 caracteres) o el backend no arranca:
#   python -c "import secrets;print(secrets.token_urlsafe(32))"
npm --prefix frontend ci
npm --prefix frontend run build
docker compose up --build
```

- App: http://127.0.0.1:8000/
- OpenAPI: http://127.0.0.1:8000/docs

## Arranque local

### Backend (:8000)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
# Dependencias fijadas con hashes (GALLAIA-SEC-005): runtime + pytest
python -m pip install --require-hashes --no-deps -r requirements-dev.lock
cp .env.example .env
# Obligatorio: rellena GALLAIA_OPERATOR_TOKEN (>=32 caracteres) o el backend no arranca:
#   python -c "import secrets;print(secrets.token_urlsafe(32))"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Al arrancar: tablas SQLite + seeds `orquestador` / `fe` / `be`.

### Frontend (:5173)

```bash
cd frontend
npm install
npm run dev
```

UI: http://127.0.0.1:5173/ (proxy `/api` → FastAPI :8000).

### LLM stub (opcional)

En `backend/.env` (nunca commit):

```env
OPENROUTER_API_KEY=
OPENROUTER_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free
```

Sin claves → runner mock.

> **Proveedores LLM:** todas las llamadas pasan por `backend/app/llm/gateway.py`: OpenRouter (principal, modelo gratuito por defecto `nvidia/nemotron-3-ultra-550b-a55b:free`) → Groq (`GROQ_API_KEY`, respaldo) → mock determinista. Cada agente puede fijar su modelo (`Agent.model`). El uso por llamada queda en la tabla `llm_usage` (`GET /api/v1/llm/usage`). `GALLAIA_LLM_BACKEND=litellm` activa el backend opcional `litellm` si está instalado. Anthropic es legacy: solo lo usa el runner AgentOS en memoria si se pide explícitamente.
>
> Nota: los modelos gratuitos de OpenRouter tienen límites de uso bajos y pueden desaparecer sin aviso; configura siempre un modelo de fallback.

## Plataforma

Kanban, sesiones, inbox, activity, triggers, grants/network/fs Isolation y demas superficies del control plane siguen disponibles. «Registrar agente» está visible pero deshabilitado («Próximamente») hasta F5.
