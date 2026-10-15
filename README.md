# GallaIA v2 — equipo agéntico personal

Herramienta personal para que **Ociel** construya software con tres agentes que se coordinan:

| Agente | Rol |
|--------|-----|
| **Orquestador** | Habla con el usuario, planifica, divide, delega a FE/BE, revisa e integra |
| **FE** | React / TypeScript / UI |
| **BE** | FastAPI / API / datos |

Stack actual: **FastAPI + SQLAlchemy/SQLite** (backend) y **React + Vite** (frontend). Runtime mock por defecto; OpenRouter como proveedor LLM principal (Groq planificado como fallback; Anthropic legacy). LangGraph / LiteLLM / MCP llegan en F2+.

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
python -m pip install -e .
cp .env.example .env
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

> **Proveedores LLM:** OpenRouter es el proveedor principal (implementado en `backend/app/providers/openrouter.py`, modelo gratuito por defecto `nvidia/nemotron-3-ultra-550b-a55b:free`). Groq está planificado como fallback (aún no implementado; se prevé una variable `GROQ_API_KEY`). Anthropic es opcional/legacy: las variables `ANTHROPIC_*` y el stub Messages siguen en el código pero no son el proveedor previsto y se eliminarán/sustituirán en un PR de código posterior. El enrutado entre proveedores se hará con LiteLLM (F2+).
>
> Nota: los modelos gratuitos de OpenRouter tienen límites de uso bajos y pueden desaparecer sin aviso; configura siempre un modelo de fallback.

## Plataforma

Kanban, sesiones, inbox, activity, triggers, grants/network/fs Isolation y demas superficies del control plane siguen disponibles. «Registrar agente» está visible pero deshabilitado («Próximamente») hasta F5.
