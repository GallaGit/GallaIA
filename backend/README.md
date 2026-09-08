# GallaAI Backend — AgentOS control plane

API HTTP (FastAPI) del control plane AgentOS (Phase 0 + Phase 1 MVP).

## Requisitos

- Python 3.11+
- SQLite (incluido; archivo en `data/gallaia.db`)

Postgres queda documentado para fases posteriores (`DATABASE_URL=postgresql+psycopg://...`).

## Setup local

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows Git Bash: source .venv/Scripts/activate
pip install -U pip
pip install -e .
cp .env.example .env
```

## Arranque

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- App: http://127.0.0.1:8000/
- OpenAPI: http://127.0.0.1:8000/docs

Al arrancar se crean tablas SQLite y se siembra el proyecto `default` con agentes `default`, `plan`, `senior-dev`.

## Docker (UI + API, un contenedor)

Flujo recomendado desde la **raíz** del repo (no desde `backend/`):

```bash
cp backend/.env.example backend/.env
npm --prefix frontend ci && npm --prefix frontend run build
docker compose up --build
```

- App (UI + API): **http://127.0.0.1:8000/** (no `:5173`)
- OpenAPI: http://127.0.0.1:8000/docs
- SQLite: `backend/data/` montado en el contenedor

Documentación de los cambios: [docs/deployment/docker.md](../docs/deployment/docker.md).  
Runbook Compose: [docs/deployment/docker-compose.md](../docs/deployment/docker-compose.md).

El `docker-compose.yml` de esta carpeta es solo API (legado).

## Endpoints AgentOS (`/api/v1`)

| Método | Ruta | Rol |
|--------|------|-----|
| GET | `/health` | Health + ping DB |
| GET | `/projects`, `/projects/{id}` | Proyectos |
| GET | `/agents`, `/agents/{id}` | Agentes (prompts reconstruidos) |
| GET/POST | `/tasks` | Listar / crear |
| GET/PATCH/DELETE | `/tasks/{id}` | CRUD parcial |
| PATCH | `/tasks/{id}/status` | Cambiar status Kanban |
| POST | `/tasks/{id}/run` | Sesión (mock, OpenRouter o Claude stub) |
| GET | `/sessions`, `/sessions/{id}` | Sesiones + tool log |
| GET | `/inbox` | Mensajes inbox |
| POST | `/inbox/{id}/reply` | Respuesta stub (no reanuda contenedor real) |

## Runtime: mock vs LLM

- Sin claves: runner **mock** que actualiza la tarea (`doing` → `done`/`review`) y escribe eventos de herramientas falsos.
- Con `OPENROUTER_API_KEY`: stub de OpenRouter Chat Completions (modelo por defecto Nemotron free). La UI usa este camino si la clave está presente.
- Con `ANTHROPIC_API_KEY` y sin OpenRouter: stub de Anthropic Messages API (no es el Agent SDK completo ni contenedores efímeros).

Los prompts de agentes están **reconstruidos** a partir del talk de Danny Postma — no son sus archivos verbatim.

## Configuración

Ver `.env.example`. CORS por defecto para Vite (`localhost:5173`).
