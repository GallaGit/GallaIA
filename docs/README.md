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

Numbered series for long-term backend documentation. Folders under `backend/app/` are **scaffold only** until implemented.

| Document | Topic |
|----------|-------|
| [backend/01-project-structure.md](backend/01-project-structure.md) | Layered layout |
| [backend/02-request-lifecycle.md](backend/02-request-lifecycle.md) | Request path |
| [backend/03-configuration.md](backend/03-configuration.md) | Settings and env |
| [backend/04-dependency-injection.md](backend/04-dependency-injection.md) | FastAPI dependencies |
| [backend/05-routing.md](backend/05-routing.md) | Routes and routers |
| [backend/06-services.md](backend/06-services.md) | Service layer |
| [backend/07-repositories.md](backend/07-repositories.md) | Data access (Temporada 2+) |
| [backend/08-data-models.md](backend/08-data-models.md) | Models vs schemas |
| [backend/09-error-handling.md](backend/09-error-handling.md) | Errors and HTTP mapping |
| [backend/10-logging.md](backend/10-logging.md) | Logging |
| [backend/11-testing.md](backend/11-testing.md) | Testing strategy |
| [backend/glossary.md](backend/glossary.md) | Backend terms |
| [backend/authentication.md](backend/authentication.md) | Auth (outside T1 series; Future until users) |

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
