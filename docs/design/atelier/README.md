# Atelier — design system (AgentOS / GallaIA)

**Status:** propuesto (UX corte AgentOS MVP)  
**Producto:** control plane AgentOS sobre GallaIA  
**Stack UI:** React + Lucide (web multiplataforma; sin exclusividad Mac)  
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

## Pantallas Fase 1

1. **Agents** — catálogo y estado de agentes  
2. **Kanban Tasks** — tablero de tareas por estado  
3. **Sessions** — sesiones / runs activos e históricos  
4. **Inbox** — cola de avisos y handoffs

## Fuera de este corte

- Implementación React (Frontend)  
- Auth, multi-tenant, deploy  
- Clonar Linear / Notion / ChatGPT pixel a pixel

## Cómo ver los mockups

Abrir `mockups/index.html` en cualquier navegador (Windows / Linux / Mac). Solo HTML + CSS; Lucide vía CDN.
