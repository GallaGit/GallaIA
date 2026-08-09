# Configuration

## Purpose

Explain how application settings are loaded from the environment, why they are centralized, and which variables exist today.

## Status

Draft (reflects current implementation)

## Scope

- Existing: `app/core/config.py` (`Settings` via pydantic-settings), `backend/.env`, `backend/.env.example`, injection via `get_settings()` (also used from Docker Compose `env_file`).
- Planned: DB URL, secrets for JWT/AI providers when those phases start.
- Future: multi-environment profiles beyond local `.env`.

## How it works

1. `Settings` subclasses `BaseSettings` and reads `backend/.env` when the process cwd is `backend/` (as with `uvicorn` / Compose).
2. Env names map to fields: `APP_NAME` → `app_name`, etc.
3. `get_settings()` is cached with `@lru_cache` (one instance per process). After changing `.env`, restart the process.

## Variables (current)

| Env var | Field | Default / role |
|---------|-------|----------------|
| `APP_NAME` | `app_name` | Display name / OpenAPI title |
| `APP_ENV` | `app_env` | e.g. `development` |
| `APP_DEBUG` | `app_debug` | Debug flag |
| `LOG_LEVEL` | `log_level` | Logging level (`INFO`, `DEBUG`, …) |

## Conventions

- Commit `.env.example` only. Never commit real secrets in `.env`.
- Prefer reading config through `Settings` / `Depends(get_settings)`, not scattered `os.getenv` calls.

## Code

- [`backend/app/core/config.py`](../../backend/app/core/config.py)
- Runbook: [`backend/README.md`](../../backend/README.md)

## TODO

- Document new settings as Fase 3+ adds database and auth.
