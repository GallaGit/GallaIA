# GallaAI Documentation

## Purpose

Index of project documentation. Prefer this file as the entry point for technical and product docs.

## Status taxonomy

| Label | Meaning |
|-------|---------|
| **Existing** | Present in the repository today (may be scaffold-only) |
| **Planned** | Intended for near-term phases; not implemented yet |
| **Future** | Later roadmap; reserved docs or folders only |

Do not treat Planned or Future items as working software.

---

## Product and planning

| Document | Description |
|----------|-------------|
| [ROADMAP.md](ROADMAP.md) | Frozen docs tree + technical roadmap (phases) |
| [alcance.md](alcance.md) | Scope: product vs Temporada 1 |
| [context.md](context.md) | Project context and principles |
| [product-vision/product-vision_v01.md](product-vision/product-vision_v01.md) | Evolving product vision |
| [glossary.md](glossary.md) | Project-wide glossary (Draft) |

---

## Architecture

| Document | Focus |
|----------|-------|
| [architecture/overview.md](architecture/overview.md) | System overview, layered stance |
| [architecture/backend.md](architecture/backend.md) | Backend package map (Fase 1+ partial Fase 2) |
| [architecture/frontend.md](architecture/frontend.md) | Frontend ↔ API (Planned) |
| [architecture/api.md](architecture/api.md) | HTTP API (`/api/v1` Existing) |
| [architecture/database.md](architecture/database.md) | Persistence (Planned, Fase 3+) |

---

## Backend deep-dives

How-to docs for the backend. Several reflect **current implementation**; others remain Planned stubs.

| Document | Topic | Doc maturity |
|----------|-------|--------------|
| [backend/project-structure.md](backend/project-structure.md) | Layered layout | Current state |
| [backend/request-lifecycle.md](backend/request-lifecycle.md) | Request path | Current state |
| [backend/configuration.md](backend/configuration.md) | Settings and env | Current state |
| [backend/dependency-injection.md](backend/dependency-injection.md) | FastAPI dependencies | Current state |
| [backend/routing.md](backend/routing.md) | Routes and routers | Current state |
| [backend/logging.md](backend/logging.md) | Logging | Current state |
| [backend/services.md](backend/services.md) | Service layer | Planned stub |
| [backend/repositories.md](backend/repositories.md) | Data access (Fase 3+) | Planned stub |
| [backend/data-models.md](backend/data-models.md) | Models vs schemas | Planned stub |
| [backend/error-handling.md](backend/error-handling.md) | Errors and HTTP mapping | Planned stub |
| [backend/testing.md](backend/testing.md) | Testing strategy | Planned stub |
| [backend/glossary.md](backend/glossary.md) | Backend terms | Draft |
| [backend/authentication.md](backend/authentication.md) | Auth (Future until users) | Planned stub |

Run instructions: [backend/README.md](../backend/README.md).

---

## Architecture Decision Records

| Document | Description |
|----------|-------------|
| [adr/README.md](adr/README.md) | ADR process and index |
| [adr/ADR-001-fastapi.md](adr/ADR-001-fastapi.md) | FastAPI (Accepted) |
| [adr/ADR-002-project-structure.md](adr/ADR-002-project-structure.md) | Layered `app/` layout (Accepted) |
| [adr/ADR-003-postgresql.md](adr/ADR-003-postgresql.md) | PostgreSQL (Proposed; Fase 3+) |

---

## Future scaffolding

Directories outside the frozen core tree (or empty topic files) may still exist from earlier scaffolding. Do not assume documented behavior until filled:

- `api/`, `database/`, `ai/`, `deployment/` (if present)

---

## TODO

- Fill remaining Draft/Planned stubs as each phase lands.
- Keep this index and [ROADMAP.md](ROADMAP.md) in sync with code.
