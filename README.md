# GallaIA — AgentOS control plane

Plataforma de aprendizaje + AgentOS MVP: control plane web (Kanban, sesiones, inbox),
inspirado en el talk de Danny Postma, con FastAPI + React.

**Multiplataforma:** Windows / Linux / macOS — solo navegador + API.
Sin Electron, Tauri ni exclusividad Mac.

## Vision

Defines agentes, creas tareas, Ejecutar ahora. Sesion mock (o stub Anthropic Messages),
tool-call log, status doing -> done/review. Inbox para decisiones humanas.

Mas detalle: [docs/product/AGENTOS.md](docs/product/AGENTOS.md)
Limites de modulo: [docs/product/MODULE_BOUNDARIES.md](docs/product/MODULE_BOUNDARIES.md)

## Stack

- Backend: Python 3.11+, FastAPI, SQLAlchemy, SQLite (Postgres later)
- Frontend: React + Vite + TypeScript + Lucide, estetica atelier
- Runtime: mock por defecto; opcional ANTHROPIC_API_KEY

## Como arrancar (Windows / Linux / macOS)

### Backend

```
cd backend
python -m venv .venv
```

Windows PowerShell: `.\.venv\Scripts\Activate.ps1`  
Linux/macOS: `source .venv/bin/activate`

```
python -m pip install -U pip
python -m pip install -e .
```

Copia `.env.example` a `.env`, luego:

```
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API: http://127.0.0.1:8000/
- Docs: http://127.0.0.1:8000/docs

### Frontend

```
cd frontend
npm install
npm run dev
```

UI: http://127.0.0.1:5173/ (Vite proxy `/api` -> FastAPI; o `VITE_API_URL`)

Build: `npm run build`

## Creditos / runtime

- Prompts RECONSTRUCTED del talk — no verbatim de Danny Postma
- Sin ANTHROPIC_API_KEY: mock runner
- Con clave: stub Messages API (no Agent SDK completo)

## Estado

- [x] Phase 0 skeleton
- [x] Phase 1 MVP (projects/agents/tasks/sessions/inbox)
- [ ] Isolation, R2, goals, triggers, YAML CLI

## Licencia

MIT
