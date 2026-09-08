# Module boundaries (teammate handoff)

## Two backend surfaces (both mounted)

1. **SQLAlchemy control plane** (frontend primary)
   - Routes: `/api/v1/projects|agents|tasks|sessions|inbox`
   - Code: `backend/app/models`, `schemas`, `services`, `api/routes/{projects,agents,tasks,sessions,inbox}.py`
   - Persistencia: SQLite `data/gallaia.db`

2. **In-memory AgentOS package** (Backend teammate contract)
   - Routes: `/api/v1/agentos/*`
   - Code: `backend/app/agentos/*` + `api/routes/agentos.py`
   - Docs: `docs/agentos/CONTRACT.md`

Do not delete either surface without coordinating. Prefer converging runners later behind one service interface.

## Frontend owns
- `frontend/src/pages/*`, `styles/atelier.css`, `api/client.ts` (calls SQLAlchemy routes)

## Entrypoints (Windows / Linux / macOS)
- `python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
- Node package scripts: install / `run dev` / `run build`
