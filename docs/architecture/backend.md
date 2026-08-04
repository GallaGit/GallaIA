# Backend Architecture

## Purpose

Describe the backend’s layered package layout, why each layer exists, and how documentation under `docs/backend/` deep-dives into each concern—without claiming a running FastAPI app today.

## Status

Draft

## Scope

- Existing: Empty scaffold mirroring:

```
app/
  api/
  core/
  db/
  models/
  schemas/
  repositories/
  services/
  providers/
  agents/
  tools/
  memory/
  rag/
  middleware/
  exceptions/
  utils/
  main.py
```

- Planned: FastAPI entrypoint, chat route, service, and one AI provider for Temporada 1; config, logging, errors as supporting pieces.
- Future: Activation of `db/`, repositories, agents, rag, memory, and tools per roadmap.

## Package roles (intended)

| Package | Role |
|---------|------|
| `api/` | HTTP routes and dependencies |
| `core/` | Config, logging, security helpers |
| `db/` | Engine/session and migrations (from Temporada 2) |
| `models/` | ORM models |
| `schemas/` | Pydantic API schemas |
| `repositories/` | Data access |
| `services/` | Use-case orchestration |
| `providers/` | External AI provider adapters |
| `agents/`, `tools/`, `memory/`, `rag/` | Reserved for later seasons |
| `middleware/`, `exceptions/`, `utils/` | Cross-cutting support |

## Deep-dives

See [docs/backend/](../backend/) (`01`–`11` and glossary).

## TODO

- Expand responsibility and import-boundary rules after first routes land.
- Mark which packages are Active vs Reserved as seasons progress.
- Do not reorganize into feature-based or hexagonal layouts.
