# Atelier — componentes Fase 1

**Status:** propuesto

## Shell

- **AppShell:** sidebar izquierda (logo Atelier / GallaAI + nav) + top bar mínima (título de vista + acciones) + main cream.
- **NavItem:** icono Lucide + label; activo = indigo + soft fill.
- Nav Phase 1 (implementado): Agents, Tasks, Sessions, Inbox; divider; **Files** + **Settings** (placeholders).
- Nav futuro (doc only, no implementar ahora): Activity, Goals, Skills, Environment, Templates, Knowledge, Ripples, Connections, Admin — ver [CONTROL_PLANE_NAV.md](../../product/CONTROL_PLANE_NAV.md). Agrupar mentalmente Operate / Configure / Govern.
## Datos

- **AgentCard:** avatar inicial, nombre, rol corto, status chip (healthy / degraded / offline), last activity.
- **StatusChip:** ok / warn / offline / coral (urgente).
- **TaskCard:** título, agente asignado, prioridad (dot coral/indigo/muted), tags opcionales.
- **KanbanColumn:** header con count; drop zone visual (solo wire — sin DnD spec).
- **SessionRow:** id mono, agente, started, duration, status.
- **InboxItem:** tipo (handoff / alert / mention), preview, timestamp, unread bar indigo.

## Acciones

- **Button primary:** indigo fill, texto paper.
- **Button secondary:** paper + line border.
- **Button danger:** coral soft + coral text (raro en Fase 1).
- **IconButton:** ghost, hover cream oscuro.

## Formularios (mínimo)

- **SearchField:** input paper, icon search muted.
- **FilterPills:** estado / agente; activo indigo-soft.

## Vacío y error

- **EmptyState:** título Fraunces + una línea + CTA secondary.
- **InlineAlert:** coral-soft para fallo de sync / sesión caída.
