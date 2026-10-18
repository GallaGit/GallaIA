# GallaIA Backend — control plane v2

API HTTP (FastAPI) del control plane GallaIA v2 (equipo Orquestador / FE / BE).

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
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- App: http://127.0.0.1:8000/
- OpenAPI: http://127.0.0.1:8000/docs

Al arrancar se crean tablas SQLite y se siembra el proyecto `default` con agentes `orquestador`, `fe`, `be` (grants + network + fs + secret refs Isolation).

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
| GET/PUT | `/agents/{id}/grants` | Grants MCP/repo/env (default deny) |
| GET/PUT | `/agents/{id}/network` | Network `open`\|`limited` + host allowlist |
| GET/PUT | `/agents/{id}/fs` | Filesystem ACL roots (default deny) |
| GET/PUT | `/agents/{id}/secrets` | Secret refs (names/keys only; never values) |
| GET/POST | `/tasks` | Listar / crear |
| GET/PATCH/DELETE | `/tasks/{id}` | CRUD parcial |
| PATCH | `/tasks/{id}/status` | Cambiar status Kanban |
| POST | `/tasks/{id}/run` | Sesión (mock, OpenRouter o Claude stub) |
| GET | `/sessions`, `/sessions/{id}` | Sesiones + tool log |
| GET | `/inbox` | Mensajes inbox |
| POST | `/inbox/{id}/reply` | Respuesta stub (no reanuda contenedor real) |

## Runtime: mock vs LLM

- Sin claves: runner **mock** que actualiza la tarea (`doing` → `done`/`review`) y escribe eventos de herramientas falsos.
- Con `OPENROUTER_API_KEY` y/o `GROQ_API_KEY`: una llamada Chat Completions por el gateway `app/llm/gateway.py` (OpenRouter → Groq → mock) con el modelo del agente (`Agent.model`; `groq/<id>` fuerza Groq, `mock` no llama a nadie, `claude-*` antiguos usan el modelo por defecto). No es el Agent SDK completo ni contenedores efímeros.
- Uso por llamada (proveedor, modelo, tokens, latencia, coste si es `:free`) en la tabla `llm_usage`; consulta en `GET /api/v1/llm/usage`.
- `GALLAIA_LLM_BACKEND=litellm` usa la librería `litellm` (opcional, `pip install litellm`); si no está instalada se sigue con HTTP directo.

Los prompts de agentes están **reconstruidos** a partir del talk de Danny Postma — no son sus archivos verbatim.

## Configuración

Ver `.env.example`. CORS por defecto para Vite (`localhost:5173`).
