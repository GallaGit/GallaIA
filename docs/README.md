# GallaAI Documentation

## Purpose

Index of project documentation. Prefer this file as the entry point for technical and product docs.

## Status taxonomy

| Label | Meaning |
|-------|---------|
| **Existing** | Present in the repository today (may be scaffold-only) |
| **Planned** | Intended for near-term AgentOS phases; not implemented yet |
| **Future** | Later roadmap / infra; reserved docs or folders only |

Do not treat Planned or Future items as working software. **Fase N = AgentOS** — see [ROADMAP.md](ROADMAP.md).

---

## Product and planning

| Document | Description |
|----------|-------------|
| [ROADMAP.md](ROADMAP.md) | **Calendario canónico AgentOS** (fases 0–7) + árbol de docs |
| [alcance.md](alcance.md) | Scope: Phase 1 AgentOS actual vs excluidos |
| [context.md](context.md) | Project context and principles |
| [product-vision/product-vision_v01.md](product-vision/product-vision_v01.md) | Evolving product vision (AgentOS first) |
| [glossary.md](glossary.md) | Project-wide glossary |

---

## AgentOS

| Document | Description |
|----------|-------------|
| [product/AGENTOS.md](product/AGENTOS.md) | Mapa de producto Phase 0–1 |
| [product/LEAD_INTAKE.md](product/LEAD_INTAKE.md) | Lead Intake: trigger + 2 agentes + score (Planned, doc only) |
| [product/CONTROL_PLANE_NAV.md](product/CONTROL_PLANE_NAV.md) | Sidebar: implementado vs doc-only |
| [product/MODULE_BOUNDARIES.md](product/MODULE_BOUNDARIES.md) | Dos superficies API + ownership |
| [agentos/README.md](agentos/README.md) | Slice MVP actual |
| [agentos/POSTMA_WALKTHROUGH.md](agentos/POSTMA_WALKTHROUGH.md) | Qué construyó Postma y orden de réplica |
| [agentos/PHASE2_PLUS.md](agentos/PHASE2_PLUS.md) | Sketch Isolation → Templates → Goals → Triggers |
| [agentos/CONTRACT.md](agentos/CONTRACT.md) | Contrato API `/api/v1/agentos` |

---

## Architecture

| Document | Focus |
|----------|-------|
| [architecture/overview.md](architecture/overview.md) | System overview, layered stance |
| [architecture/backend.md](architecture/backend.md) | Backend package map (AgentOS MVP) |
| [architecture/frontend.md](architecture/frontend.md) | React+Vite atelier ↔ API |
| [architecture/api.md](architecture/api.md) | HTTP API (`/api/v1`, AgentOS, errors) |
| [architecture/database.md](architecture/database.md) | SQLite Existing; Postgres Proposed (ADR-003) |

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
| [backend/services.md](backend/services.md) | Service layer | AgentOS-oriented |
| [backend/repositories.md](backend/repositories.md) | Data access | AgentOS-oriented |
| [backend/data-models.md](backend/data-models.md) | Models vs schemas | AgentOS-oriented |
| [backend/error-handling.md](backend/error-handling.md) | Errors and HTTP mapping | Current state |
| [backend/testing.md](backend/testing.md) | Testing strategy | AgentOS-oriented |
| [backend/glossary.md](backend/glossary.md) | Backend terms | Draft |
| [backend/authentication.md](backend/authentication.md) | Auth (Future, single operator) | Planned stub |

Run instructions: [backend/README.md](../backend/README.md).

---

## Architecture Decision Records

| Document | Description |
|----------|-------------|
| [adr/README.md](adr/README.md) | ADR process and index |
| [adr/ADR-001-fastapi.md](adr/ADR-001-fastapi.md) | FastAPI (Accepted) |
| [adr/ADR-002-project-structure.md](adr/ADR-002-project-structure.md) | Layered `app/` layout (Accepted) |
| [adr/ADR-003-postgresql.md](adr/ADR-003-postgresql.md) | PostgreSQL (Proposed; infra/Future, not AgentOS Fase 3) |

---

## Design

| Document | Description |
|----------|-------------|
| [design/atelier/README.md](design/atelier/README.md) | Atelier design system |
| [design/atelier/screens.md](design/atelier/screens.md) | Pantallas Phase 1 + EmptyStates futuros |

---

## Future scaffolding

Directories outside the core tree (or empty topic files) may still exist from earlier scaffolding. Do not assume documented behavior until filled:

- `api/`, `database/`, `ai/` (if present) — e.g. empty RAG stubs remain Future

---

## Deployment

| Document | Description |
|----------|-------------|
| [deployment/docker.md](deployment/docker.md) | Imagen única UI+API: cambios, archivos, arquitectura |
| [deployment/docker-compose.md](deployment/docker-compose.md) | Runbook `docker compose up` |
| [deployment/environments.md](deployment/environments.md) | Local vs Docker y variables |
| [deployment/ci-cd.md](deployment/ci-cd.md) | CI/CD (placeholder) |

---

## TODO

- Fill remaining Draft/Planned stubs as each AgentOS phase lands.
- Keep this index and [ROADMAP.md](ROADMAP.md) in sync with code.
