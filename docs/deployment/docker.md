# Docker — GallaAI

Una sola imagen, un solo contenedor: **UI (React/Vite) + API (FastAPI)** con SQLite.

Runbook operativo: [docker-compose.md](./docker-compose.md).

## Resumen del cambio

Antes el Docker vivía solo bajo `backend/` (API + Postgres no cableado). Ahora el flujo recomendado es:

| Antes | Ahora |
|-------|--------|
| `backend/Dockerfile` + `backend/docker-compose.yml` | `Dockerfile` + `docker-compose.yml` en la **raíz** |
| Solo API en `:8000` | UI + API en `:8000` |
| Postgres en compose (sin `DATABASE_URL` al host `db`) | SQLite MVP + volumen `backend/data` |
| Frontend aparte (`npm run dev` :5173) | SPA embebida en el mismo contenedor |

El compose/API-only de `backend/` queda como **legado** (solo API). Preferir la raíz.

## Arranque rápido

```bash
# desde la raíz del repo
cp backend/.env.example backend/.env
npm --prefix frontend ci && npm --prefix frontend run build
docker compose up --build
# o: bash scripts/docker-up.sh
```

Abre **http://127.0.0.1:8000/** (UI). OpenAPI: http://127.0.0.1:8000/docs.

No uses `:5173` con Docker; ese puerto es solo Vite en desarrollo local.

## Archivos tocados

| Archivo | Rol |
|---------|-----|
| [`Dockerfile`](../../Dockerfile) | Imagen única: Python + `frontend/dist` → `/app/static` |
| [`docker-compose.yml`](../../docker-compose.yml) | Servicio `app`, puerto `8000`, `env_file` + volumen SQLite |
| [`.dockerignore`](../../.dockerignore) | Excluye venv, `node_modules`, `.env`, DBs locales |
| [`scripts/docker-up.sh`](../../scripts/docker-up.sh) | Atajo: build Vite + `docker compose up` |
| [`backend/app/main.py`](../../backend/app/main.py) | Sirve SPA si existe `STATIC_DIR` (`index.html`, `/assets`, fallback rutas cliente) |
| `backend/Dockerfile` / `backend/docker-compose.yml` | Legado API-only |

## Cómo funciona la imagen

1. En el **host**: `npm run build` genera `frontend/dist` (`VITE_API_URL` vacío → fetch same-origin `/api/...`).
2. Docker copia ese `dist` a `/app/static`, instala el backend con `pip install .` y arranca uvicorn en `0.0.0.0:8000`.
3. FastAPI atiende `/api/v1/*`, `/health`, `/docs` y sirve la SPA desde static.

Variable de runtime: `STATIC_DIR=/app/static` (por defecto en la imagen).

### Por qué el build de Vite no va dentro de Docker

En algunos entornos Windows / Docker Desktop / proxy, `npm ci` / `npm install` dentro de BuildKit falla (`Exit handler never called` / SSL). Por eso el frontend se construye en el host y se **copia** a la imagen. El **runtime** sigue siendo un solo contenedor.

`PIP_TRUSTED_HOST` en el Dockerfile mitiga el mismo tipo de problema SSL al instalar paquetes Python.

## Persistencia y config

- SQLite: volumen `./backend/data` → `/app/data`
- Env: `backend/.env` (nunca commitear secretos; usar `.env.example`)
- Healthcheck: `GET /health`

## Verificación

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/health
curl -I http://127.0.0.1:8000/
docker compose ps   # un servicio: app, status healthy
```

## Fuera de alcance (MVP)

- Multi-servicio (nginx + api + db) en Compose
- Postgres cableado en Compose (ver ADR-003 / fases posteriores)
- Publicar imágenes a un registry / CI
