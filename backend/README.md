# GallaAI Backend

API HTTP del proyecto (FastAPI). Fase 1 Foundation completada; Fase 2 API Base iniciada.

## Requisitos

- Python 3.11+ (local)
- Git Bash o terminal equivalente en Windows
- Docker Desktop (opcional, para Compose)

## Setup local (venv)

Desde este directorio (`backend/`):

```bash
python -m venv .venv
source .venv/Scripts/activate   # Git Bash en Windows
pip install -U pip
pip install "fastapi[standard]" pydantic-settings
cp .env.example .env            # si aún no tienes .env
```

El prompt debe mostrar `(.venv)`. `python` y `pip` deben apuntar a `backend/.venv/...`.

Si mueves el repositorio de carpeta, borra `.venv` y vuelve a crearlo (los venv de Windows guardan rutas absolutas).

## Arranque local

```bash
source .venv/Scripts/activate
uvicorn app.main:app --reload
```

- App: http://127.0.0.1:8000/
- Docs OpenAPI: http://127.0.0.1:8000/docs

## Arranque con Docker

Con Docker Desktop en marcha, y **sin** uvicorn local en el puerto 8000:

```bash
docker compose up --build
docker compose down
```

## Endpoints actuales

| Método | Ruta | Rol |
|--------|------|-----|
| GET | `/` | Ping simple |
| GET | `/health` | Health de infra (sin versionar) |
| GET | `/api/v1/health` | Health dentro de la API v1 |

## Configuración

- Variables en `backend/.env` (no se sube a git).
- Plantilla pública: `backend/.env.example`.
- Lectura centralizada: `app/core/config.py` (`Settings` + `get_settings()`).

Variables actuales: `APP_NAME`, `APP_ENV`, `APP_DEBUG`, `LOG_LEVEL`.

## Documentación

- Roadmap técnico: [docs/ROADMAP.md](../docs/ROADMAP.md)
- Arquitectura backend: [docs/architecture/backend.md](../docs/architecture/backend.md)
- Deep-dives: [docs/backend/](../docs/backend/)
