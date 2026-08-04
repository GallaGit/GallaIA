# GallaAI Documentation

## Purpose

Index of project documentation. Prefer this file as the entry point for technical and product docs.

## Status taxonomy

| Label | Meaning |
|-------|---------|
| **Existing** | Present in the repository today (may be scaffold-only) |
| **Planned** | Intended for near-term seasons (especially Temporada 1–2); not implemented yet |
| **Future** | Later roadmap; reserved docs or folders only |

Do not treat Planned or Future items as working software.

---

## Product (Existing content)

| Document | Description |
|----------|-------------|
| [alcance.md](alcance.md) | Scope: product vs Temporada 1 |
| [context.md](context.md) | Project context and principles |
| [product-vision/product-vision_v01.md](product-vision/product-vision_v01.md) | Evolving product vision |
| [glossary.md](glossary.md) | Project-wide glossary (Draft) |

---

## Architecture (Draft stubs)

| Document | Focus |
|----------|-------|
| [architecture/overview.md](architecture/overview.md) | System overview, layered stance |
| [architecture/backend.md](architecture/backend.md) | Backend package map |
| [architecture/frontend.md](architecture/frontend.md) | Frontend ↔ API (Planned) |
| [architecture/api.md](architecture/api.md) | HTTP API architecture (Planned) |
| [architecture/database.md](architecture/database.md) | Persistence from Temporada 2 (Planned) |

---

## Backend deep-dives (Draft stubs)

Backend documentation stubs. Folders under `backend/app/` are **scaffold only** until implemented.

| Document | Topic |
|----------|-------|
| [backend/project-structure.md](backend/project-structure.md) | Layered layout |
| [backend/request-lifecycle.md](backend/request-lifecycle.md) | Request path |
| [backend/configuration.md](backend/configuration.md) | Settings and env |
| [backend/dependency-injection.md](backend/dependency-injection.md) | FastAPI dependencies |
| [backend/routing.md](backend/routing.md) | Routes and routers |
| [backend/services.md](backend/services.md) | Service layer |
| [backend/repositories.md](backend/repositories.md) | Data access (Temporada 2+) |
| [backend/data-models.md](backend/data-models.md) | Models vs schemas |
| [backend/error-handling.md](backend/error-handling.md) | Errors and HTTP mapping |
| [backend/logging.md](backend/logging.md) | Logging |
| [backend/testing.md](backend/testing.md) | Testing strategy |
| [backend/glossary.md](backend/glossary.md) | Backend terms |
| [backend/authentication.md](backend/authentication.md) | Auth (Future until users) |

---

## Architecture Decision Records

| Document | Description |
|----------|-------------|
| [adr/README.md](adr/README.md) | ADR process and index |
| [adr/ADR-001-fastapi.md](adr/ADR-001-fastapi.md) | FastAPI (Proposed) |
| [adr/ADR-002-postgresql.md](adr/ADR-002-postgresql.md) | PostgreSQL (Proposed; Temporada 2+) |

---

## Future scaffolding (empty topic files)

These directories exist for later seasons. Files are placeholders; do not assume documented behavior.

- `api/` — conventions, endpoints, pagination, filtering, versioning
- `database/` — models, migrations, relationships, indexing
- `ai/` — providers, prompts, embeddings, rag, tools, memory
- `deployment/` — docker, docker-compose, environments, ci-cd

---

## TODO

- Fill Draft stubs as each season implements the corresponding capability.
- Promote ADRs from Proposed to Accepted when decisions are confirmed in code.
- Keep this index updated when new docs are added.
