# Glossary

## Purpose

Define project-wide terms used across GallaAI documentation so product, architecture, and backend docs share one vocabulary.

Backend-specific terms: [backend/glossary.md](backend/glossary.md).

## Status

Draft

## Scope

- Existing: AgentOS control-plane terms used in [AGENTOS.md](product/AGENTOS.md), [ROADMAP.md](ROADMAP.md), and the root README.
- Planned: Terms for Isolation / templates / goals / triggers as those phases are documented and built.
- Future: RAG, embedding, product-chat terms when those packages activate.

## Seed entries

| Term | Working definition |
|------|--------------------|
| **Temporada / Fase** | Entrega acotada del [ROADMAP](ROADMAP.md). **Fase N = AgentOS** (no “Fase 3 = Postgres”). |
| **Existing / Planned / Future** | Etiquetas de madurez de docs: en el repo vs previsto vs más tarde |
| **Layered architecture** | Layout por capa técnica (`api`, `services`, `repositories`, …), no por feature ([ADR-002](adr/ADR-002-project-structure.md)) |
| **Agent** | Rol con prompts fundacional + de rol; un solo trabajo |
| **Task** | Card Kanban: `todo` \| `doing` \| `review` \| `done` |
| **Session** | Un run de agente + log de tool-calls |
| **Inbox** | Canal de interrupción / decisión humana |
| **Activity** | Feed global cronológico (≠ Inbox, ≠ Session) |
| **Goal** | Loop abierto con DoD aprobado + orquestador (≠ Task) |
| **Skill** | Capacidad reutilizable `prompt`\|`file` (≠ Agent) |
| **Environment** | Política de red + env inyectado al start |
| **Template** | Receta que instancia una cadena de tasks con gates |
| **Knowledge** | Corpus / wiki del operador (RAG = Future) |
| **Ripple** | Grafo causa→efecto (≠ Activity) |
| **Connection** | MCP / repo / secret ref nombrado; grants por agente |
| **Isolation** | Default deny: grants MCP/repo/env/fs + muro de red |
| **Admin** | Gobierno del único operador (absorbe Settings) |

Detalle de pantallas: [CONTROL_PLANE_NAV.md](product/CONTROL_PLANE_NAV.md).

## TODO

- Expand definitions as docs mature; keep entries short.
- Prefer linking to ADRs or deep-dives over duplicating decisions here.
- Sync naming with [backend/glossary.md](backend/glossary.md).
