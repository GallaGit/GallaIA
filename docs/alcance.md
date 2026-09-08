# Alcance del Proyecto

## Resumen

**GallaAI** es la marca y el nombre del producto. Es una plataforma de aprendizaje + **control plane AgentOS**, orientada a operar agentes (Kanban, sesiones, inbox) y a crecer por fases. El alcance de cada fase se limita a lo necesario antes de avanzar.

Este documento define **qué entra**, **qué no entra** y **cómo se acota** el trabajo, con énfasis en la fase actual.

Calendario canónico: [ROADMAP.md](ROADMAP.md). Mapa de producto: [product/AGENTOS.md](product/AGENTOS.md).

---

## Alcance del producto (visión a largo plazo)

La plataforma puede evolucionar hacia capacidades de chat, RAG, memoria e integraciones. **No** se busca clonar ChatGPT ni un SaaS multi-tenant en esta etapa. El aprendizaje se materializa hoy como **AgentOS** (plano de control sobre runners mock / stub).

Capacidades previstas a lo largo del ciclo (solo cuando el [ROADMAP](ROADMAP.md) lo indique):

- Control plane: agentes, tasks, sessions, inbox
- Isolation, templates, goals, triggers, YAML/CLI
- Persistencia más fuerte (Postgres cuando SQLite no baste)
- Auth de un operador, PWA, live viewer
- Más adelante: RAG, embeddings, chat de producto, automatizaciones ricas

### Fuera del alcance general del proyecto

- Proyectos desechables o demos aisladas que no se integren a la aplicación única
- Complejidad innecesaria o funcionalidades “por adelantado”
- Replicar de forma completa cualquier producto comercial (Postma, Linear, ChatGPT)
- Cursor Cloud Agents, runners solo-Mac, Electron/Tauri, LangGraph como camino del MVP
- Multi-tenant / billing SaaS

---

## Alcance de la fase actual: AgentOS Phase 1

**Objetivo:** control plane AgentOS usable en local (Kanban + seeds + run + session log + inbox).

**Versión de referencia:** MVP en rama `feat/agentos-mvp` (ver [product/AGENTOS.md](product/AGENTOS.md)).

### Incluido

- Backend **FastAPI** (Python) con `/api/v1` y `/api/v1/agentos`
- Frontend **React + Vite + TypeScript + Lucide** (estética atelier)
- Persistencia **SQLite** (`data/gallaia.db`) para el control plane SQLAlchemy
- Seeds: `default`, `plan`, `senior-dev` (prompts RECONSTRUCTED)
- Kanban `todo → doing → review → done` + **Ejecutar ahora**
- Sessions con tool-event log; Inbox list + reply stub
- Runner **mock** (default); stub Anthropic Messages opcional
- Docker / Compose (UI + API)

### Excluido (hasta completar Phase 1 / no implementar Phase 2+ ahora)

- Isolation real (ACL MCP/red/filesystem, secret store)
- Templates con gates, Goals + orquestador, Triggers/webhooks
- YAML CLI, PWA push, live SSE / Activity feed completo
- RAG, embeddings, chat tipo ChatGPT como producto
- Auth multi-usuario, PostgreSQL obligatorio, multi-tenant
- Agent SDK / Managed Agents completo (solo stub Messages)

Detalle Phase 2+: [agentos/PHASE2_PLUS.md](agentos/PHASE2_PLUS.md). Sidebar futuro (doc only): [product/CONTROL_PLANE_NAV.md](product/CONTROL_PLANE_NAV.md).

### Criterio de éxito (definición de “hecho”)

La Phase 1 se considera completada cuando el operador pueda:

1. Abrir la aplicación (local o Docker)
2. Ver agentes seed / crear una task en Kanban
3. Lanzar **Ejecutar ahora** (mock o stub)
4. Ver la session con tool log y el avance de estado en el tablero
5. Ver items relevantes en Inbox cuando aplique (review / waiting-inbox)

---

## Stack dentro de alcance (base técnica)

| Capa | Tecnología |
|------|------------|
| Backend | Python, FastAPI |
| Frontend | React, Vite, TypeScript, Lucide |
| Persistencia actual | SQLite |
| Persistencia futura | PostgreSQL ([ADR-003](adr/ADR-003-postgresql.md), Proposed) |
| IA | Mock; opcional Anthropic Messages stub |
| DevOps | Docker, Docker Compose |

**No** Next.js en el stack actual del control plane.

---

## Límites de proceso

- Una funcionalidad a la vez
- Cada entrega debe quedar integrada, documentada y funcional antes de la siguiente
- Documentar decisiones importantes
- Priorizar comprensión del problema y del diseño antes que velocidad
- Phase 2+ = **documentación primero**; no implementar Isolation/Goals/Triggers en el MVP

---

## Relación con otros documentos

| Documento | Rol |
|-----------|-----|
| [README.md](../README.md) | Arranque y visión corta |
| [ROADMAP.md](ROADMAP.md) | Calendario AgentOS (fases 0–7) |
| [context.md](context.md) | Propósito, filosofía, fase actual |
| [product/AGENTOS.md](product/AGENTOS.md) | Mapa de producto Phase 1 |
| [product-vision/](product-vision/) | Visión de producto (en evolución) |
| [alcance.md](alcance.md) | Este documento: límites de qué se construye y cuándo |

---

## Notas de mantenimiento

Cuando se cierre una fase o se amplíe el alcance, actualizar este archivo para:

1. Marcar la fase AgentOS activa
2. Ajustar incluidos / excluidos
3. Redefinir el criterio de éxito de la nueva fase
4. Mantener numeración alineada con [ROADMAP.md](ROADMAP.md) (no reintroducir “Fase 3 = Postgres”)
