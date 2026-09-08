# Docker Compose — GallaAI (una imagen, un contenedor)

API FastAPI + UI React (build Vite) en el **mismo** contenedor. SQLite en volumen.

Visión y changelog: [docker.md](./docker.md).

## Requisitos

- Docker Desktop (o Engine + Compose v2)
- Node.js (solo para construir el frontend **antes** de la imagen)
- `backend/.env` (copiar desde `backend/.env.example`)

## Arranque (desde la raíz del repo)

```bash
cp backend/.env.example backend/.env   # si aún no existe
npm --prefix frontend ci
npm --prefix frontend run build
docker compose up --build
```

Atajo: `bash scripts/docker-up.sh` o `bash scripts/docker-up.sh -d`.

Parar: `docker compose down`.

Recrear limpio: `docker compose up --build -d --force-recreate`.

## Qué obtiene

| URL | Contenido |
|-----|-----------|
| http://127.0.0.1:8000/ | UI AgentOS (SPA) |
| http://127.0.0.1:8000/agents | Ruta SPA (React Router) |
| http://127.0.0.1:8000/health | Health JSON |
| http://127.0.0.1:8000/api/v1/health | Health + DB |
| http://127.0.0.1:8000/api/v1/agentos/* | Superficie AgentOS (UI) |
| http://127.0.0.1:8000/docs | OpenAPI |

Un solo servicio Compose: **`app`**. No hace falta `npm run dev` ni un segundo contenedor.

## Compose (`docker-compose.yml` raíz)

```yaml
services:
  app:
    build: .
    ports: ["8000:8000"]
    env_file: [backend/.env]
    volumes: [./backend/data:/app/data]
```

- Healthcheck HTTP a `/health`
- `restart: unless-stopped`

## Persistencia

- Volumen bind: `./backend/data` → `/app/data`
- Base: `DATABASE_URL=sqlite:///./data/gallaia.db` en `backend/.env`

## Imagen (`Dockerfile` raíz)

1. Host genera `frontend/dist` (Vite; same-origin `/api`)
2. Imagen Python: `pip install .` + copia `dist` → `/app/static`
3. CMD: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

SPA: `STATIC_DIR` + montaje `/assets` y fallback de rutas cliente en `backend/app/main.py`.

## Desarrollo local sin Docker

Sigue válido: backend con uvicorn + frontend con Vite en `:5173` (proxy `/api` → `:8000`). Ver README raíz.

El compose bajo `backend/` es solo API (legado); el flujo recomendado es el de la **raíz**.

## Troubleshooting

| Síntoma | Qué revisar |
|---------|-------------|
| Página en blanco / no carga | URL correcta: **http://127.0.0.1:8000/** (no `:5173`) |
| `npm` falla *dentro* del build Docker | Esperado en algunos Windows/proxy; construye `frontend/dist` en el host |
| Puerto 8000 ocupado | `docker compose down`; mata otros uvicorn/APIs en 8000 |
| DB no persiste | Comprueba que exista el volumen `backend/data` |
| API ok pero UI vieja | `npm --prefix frontend run build` y `docker compose up --build --force-recreate` |
