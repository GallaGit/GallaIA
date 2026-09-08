# Atelier — design system (AgentOS / GallaIA)

**Status:** propuesto (UX corte AgentOS MVP)  
**Producto:** control plane AgentOS sobre GallaIA  
**Stack UI:** React + Vite + Lucide (web multiplataforma; sin exclusividad Mac)  
**Rama:** `feat/agentos-mvp`

## Principio

Atelier = taller de trabajo: papel crema, tinta índigo, acento coral. Clara, densa donde hace falta, nunca Linear-oscuro ni clon de Leads_CRM.

## Entregables

| Artefacto | Ruta |
|-----------|------|
| Tokens | [tokens.md](./tokens.md) |
| Componentes | [components.md](./components.md) |
| Pantallas clave | [screens.md](./screens.md) |
| Wireframes HTML | [mockups/](./mockups/) |
| Nav futuro (doc only) | [CONTROL_PLANE_NAV.md](../../product/CONTROL_PLANE_NAV.md) |

## Pantallas Fase 1 (implementadas en React)

1. **Agents** — catálogo y estado de agentes  
2. **Kanban Tasks** — tablero de tareas por estado  
3. **Sessions** — sesiones / runs activos e históricos  
4. **Inbox** — cola de avisos y handoffs  
5. **Files** / **Settings** — EmptyState placeholders

El frontend atelier **ya existe** bajo `frontend/` (no está “fuera de corte”). Las pantallas Activity, Goals, Skills, Environment, Templates, Knowledge, Ripples, Connections, Admin son **solo documentación** hasta su fase — ver [CONTROL_PLANE_NAV.md](../../product/CONTROL_PLANE_NAV.md).

## Fuera de este corte UX

- Auth, multi-tenant, deploy productivo  
- Clonar Linear / Notion / ChatGPT pixel a pixel  
- Implementar Phase 2+ (Isolation, Goals, etc.)

## Cómo ver los mockups

Abrir `mockups/index.html` en cualquier navegador (Windows / Linux / Mac). Solo HTML + CSS; Lucide vía CDN.
