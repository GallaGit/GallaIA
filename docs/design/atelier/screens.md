# Pantallas clave — AgentOS Fase 1

**Status:** propuesto  
**Criterio UX:** operador ve agentes, mueve trabajo en kanban, inspecciona sesiones, vacía inbox — sin clonar Linear.

## 1. Agents (`/agents`)

**Job:** panorama del fleet.

- Grid de AgentCards (2–3 cols desktop; 1 col estrecho).
- Filtros: All / Healthy / Degraded / Offline.
- Click card → drawer o ruta detalle (Fase 1: drawer con bio corta + últimas 3 sessions + link a Tasks filtradas).
- Empty: “Aún no hay agentes” + CTA “Registrar agente” (copy; wire only).

## 2. Kanban Tasks (`/tasks`)

**Job:** flujo de trabajo por estado.

Columnas (alineadas al API backend Fase 1: `todo|doing|review|done`):

| UI label | Status API | Significado |
|----------|------------|-------------|
| Backlog | `todo` | Sin empezar |
| Doing | `doing` | En curso |
| Review | `review` | En revisión |
| Done | `done` | Hecho |

- **No** columna Blocked en Fase 1 (no existe en API).
- Card muestra título + agente + prioridad.
- Header de board: Search + “New task” primary.
- No swimlanes por agente en Fase 1.

## 3. Sessions (`/sessions`)

**Job:** runs / conversaciones de agentes (mock data ok).

- Tabla densa: Session ID · Agent · Started · Duration · Status (running / ended / failed).
- Fila failed → InlineAlert pattern en detalle.
- Click → panel: timeline corta (started → tool calls stub → ended).

## 4. Inbox (`/inbox`)

**Job:** cola de atención humana.

Tipos:

- **Handoff** — agente pide humano
- **Alert** — sesión failed / degraded
- **Mention** — nota @operador (mock)

- Lista + panel lectura; unread indigo bar.
- Acciones: Acknowledge / Open session / Snooze (wire).

## Navegación IA (happy path)

1. Abre Agents → ve 1 degraded  
2. Inbox ya tiene Alert de esa sesión  
3. Tasks: mueve card a Review o asigna follow-up  
4. Sessions: abre run failed y confirma causa stub  

## No-go visual

- Fondo `#0B1220` / sidebar negra tipo Linear  
- Teal ops de Leads_CRM / multiagente  
- Glassmorphism / gradients pesados


## 5. Files (`/files`) — placeholder

EmptyState: “Files llega en Isolation (Fase 2)” + sin upload real. Solo shell + empty.

## 6. Settings (`/settings`) — placeholder

Lista mínima (tema Atelier locked, API base URL mock read-only). Sin auth forms. Futuro: absorbido por **Admin**.

## 7–15. Pantallas futuras (EmptyState / doc only)

No implementar rutas ni CRUD. Spec de producto: [CONTROL_PLANE_NAV.md](../../product/CONTROL_PLANE_NAV.md).

| # | Ruta | Job corto | Fase |
|---|------|-----------|------|
| 7 | `/activity` | Feed global | 7 |
| 8 | `/goals` | Gauntlet / DoD | 4 |
| 9 | `/skills` | Capacidades reutilizables | 3 |
| 10 | `/environment` | Red + env secrets | 2 |
| 11 | `/templates` | Cadenas + gates | 3 |
| 12 | `/knowledge` | Corpus / wiki | 2+ (RAG Future) |
| 13 | `/ripples` | Grafo causa→efecto | 5 |
| 14 | `/connections` | MCP + repos + secret refs | 2 |
| 15 | `/admin` | Gobierno operador (absorbe Settings) | 1 copy → 2/6 |

Cada una, si aparece en shell, usa **EmptyState** (“Documentado — no implementado”) + pill atelier. Sin API.
