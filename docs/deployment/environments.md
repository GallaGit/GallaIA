# Environments

## Local (sin Docker)

- Backend: uvicorn en `127.0.0.1:8000`, SQLite en `backend/data/gallaia.db`
- Frontend: Vite en `127.0.0.1:5173`, proxy `/api` → backend
- Config: `backend/.env` (desde `.env.example`)

## Docker (recomendado)

- Un contenedor `app`: UI + API en **http://127.0.0.1:8000/**
- Misma `backend/.env`; SQLite vía volumen `backend/data`
- Detalle: [docker.md](./docker.md) y [docker-compose.md](./docker-compose.md)

## Variables relevantes

| Variable | Uso |
|----------|-----|
| `DATABASE_URL` | MVP: `sqlite:///./data/gallaia.db` |
| `CORS_ORIGINS` | Necesario sobre todo con Vite `:5173`; en Docker same-origin suele bastar |
| `STATIC_DIR` | En imagen Docker: `/app/static` |
| `ANTHROPIC_API_KEY` | Opcional; sin clave → runner mock |
| `VITE_API_URL` | Vacío en build Docker → `/api` same-origin |

Nunca commitear `.env` con secretos.
