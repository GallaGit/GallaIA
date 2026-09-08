# Project Structure

## Purpose

Explain why the backend uses a layered package layout under `backend/app/`, what each package owns, and what is active today versus reserved for later phases.

## Status

Draft (reflects current implementation)

## Scope

- Existing: Layered tree under `backend/app/` with active `main`, `core` (config/logging), `api` (router, routes, dependencies), `agentos/`, `exceptions/`, `middleware/`, plus control-plane `models` / `schemas` / `services` and SQLite. Docker and `pyproject.toml` at `backend/` (root Compose serves UI+API).
- Planned: Isolation grants, templates, goals per [ROADMAP.md](../ROADMAP.md).
- Future: `providers/` richness, `memory/`, `rag/`; Postgres per [ADR-003](../adr/ADR-003-postgresql.md).
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
│   ├── db/ …                   # SQLite control plane (Postgres = Future ADR-003)
│   ├── agentos/ …              # in-memory AgentOS MVP package
│   ├── models/ schemas/ repositories/ services/ …
│   └── …
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── .env.example
└── README.md
```

## Rules of thumb

- Routes stay thin; business logic lives in `services/` / `agentos/`.
- Persistence stays out of routes where practical (repositories + DB session).
- Do not migrate to feature-based, hexagonal, CQRS, or DDD layouts ([ADR-002](../adr/ADR-002-project-structure.md)).

## TODO

- Update the active/reserved table when new packages gain real code.
- Keep aligned with [architecture/backend.md](../architecture/backend.md).
