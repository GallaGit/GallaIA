# Project Structure

## Purpose

Explain why the backend uses a layered package layout under `backend/app/`, what each package owns, and what is active today versus reserved for later phases.

## Status

Draft (reflects current implementation)

## Scope

- Existing: Layered tree under `backend/app/` with active `main`, `core` (config/logging), `api` (router, routes, dependencies), `exceptions/`, and `middleware/`. Docker and `pyproject.toml` at `backend/`.
- Planned: `services/`, then `db/` / `repositories/` / `models/` / `schemas/`.
- Future: `providers/`, `agents/`, `tools/`, `memory/`, `rag/`.

## Layout (simplified)

```text
backend/
├── app/
│   ├── main.py                 # FastAPI app + lifespan + handlers
│   ├── api/
│   │   ├── router.py           # mounts v1 routers
│   │   ├── dependencies/       # SettingsDep, …
│   │   └── routes/             # endpoint modules
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── security.py         # scaffold
│   ├── exceptions/             # AppError + handlers
│   ├── middleware/             # request-id
│   ├── db/ …                   # scaffold (Fase 3+)
│   ├── models/ schemas/ repositories/ services/ …
│   └── …
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── .env.example
└── README.md
```

## Rules of thumb

- Routes stay thin; business logic will live in `services/` when introduced.
- Persistence stays out of routes (repositories + DB session, Fase 3+).
- Do not migrate to feature-based, hexagonal, CQRS, or DDD layouts ([ADR-002](../adr/ADR-002-project-structure.md)).

## TODO

- Update the active/reserved table when new packages gain real code.
- Keep aligned with [architecture/backend.md](../architecture/backend.md).
