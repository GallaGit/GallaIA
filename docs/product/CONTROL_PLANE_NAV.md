# Control plane navigation — mapa del sidebar

**Status:** documentación only. **No implementar** las rutas nuevas en este PR.

Define qué pantallas tendrá el sidebar del control plane AgentOS, qué hace cada una, en qué fase entra, y cómo se distingue de las demás. Calendario: [ROADMAP.md](../ROADMAP.md). Réplica Postma: [POSTMA_WALKTHROUGH.md](../agentos/POSTMA_WALKTHROUGH.md). Sketch corto: [PHASE2_PLUS.md](../agentos/PHASE2_PLUS.md).

Shell FE con PlaceholderPage / rutas 404 = PR de frontend futuro, no este documento.

---

## Grupos del nav

```text
OPERATE              CONFIGURE             GOVERN
Inbox *              Skills                Admin
Tasks *              Environment
Agents *             Templates
Sessions *           Knowledge
Files ~              Connections
Activity
Goals
Ripples
```

`*` implementado (Phase 1) · `~` placeholder ya existente · resto = **doc only**

| Ruta hoy | Estado |
|----------|--------|
| `/agents`, `/tasks`, `/sessions`, `/inbox` | Implementado |
| `/files`, `/settings` | Placeholder EmptyState |
| Activity, Goals, Skills, Environment, Templates, Knowledge, Ripples, Connections, Admin | Solo este doc |

**Admin** absorbe `/settings` cuando se implemente. **Sessions** no se quita del nav: es el viewer de un run.

---

## Mapping vs Postma

Postma partía MCPs y Repos; GallaIA los unifica. Ripples / Knowledge / Admin son superficies propias.

| GallaIA | Postma (aprox.) |
|---------|-----------------|
| Connections | MCPs + Repos + secret refs |
| Knowledge | Wiki del `librarian` + corpus (RAG = Future) |
| Ripples | Triggers + automations + fan-out (sin nombre en el video) |
| Admin | Settings + YAML/CLI sync + runner config (un operador) |
| Activity | Activity feed (Fase 7) |
| Environment | Environment / network policy |
| Skills | Skills |
| Templates | Task templates / compound engineer |
| Goals | Goals / gauntlet loop |

---

## Implementado (Phase 1)

### Inbox (`/inbox`)

**Job:** único canal de interrupción humana (handoff, decisión, gate).  
**No es:** progreso rutinario (eso es Activity / task.activity).  
**Fase:** 1 (list + reply stub); resume real + PWA en Fase 7.  
**Done when (hoy):** listar sessions `waiting-inbox` + tasks en `review`.  
**Non-goal:** Slack paralelo, spam de progreso.

### Tasks (`/tasks`)

**Job:** Kanban `todo → doing → review → done` + asignar + Ejecutar ahora.  
**No es:** Goal (loop abierto) ni Template (receta).  
**Fase:** 1.  
**Done when:** run mock avanza card y crea session.  
**Contrato:** [CONTRACT.md](../agentos/CONTRACT.md).

### Agents (`/agents`)

**Job:** catálogo de roles (seeds + detalle prompts).  
**No es:** Skill (capacidad reutilizable) ni Connection (MCP/repo).  
**Fase:** 1 (seeds); ACL ricos en Fase 2.  
**Done when:** ver `default` / `plan` / `senior-dev` con prompts RECONSTRUCTED.

### Sessions (`/sessions`)

**Job:** un run concreto + tool-event log (replay).  
**No es:** Activity (feed global) ni Ripples (grafo causa→efecto).  
**Fase:** 1; live SSE en Fase 7.  
**Done when:** tras un run, la session muestra `tool_events`.

### Files (`/files`)

**Job (futuro):** browser del filesystem persistente (R2 + MCP ACL).  
**Hoy:** EmptyState. **Fase real:** 2.  
**No es:** Knowledge (corpus indexado / wiki de producto).

### Settings (`/settings`)

**Job hoy:** placeholder (tema, API base read-only).  
**Futuro:** absorbido por **Admin**.

---

## Documentado — no implementar ahora

Cada ficha: job · qué no es · fase · done when · non-goal.

### Activity (`/activity`) — Fase 7

**Job:** feed global cronológico (task transitions, session start/end, inbox events, luego goals/templates/ripples).  
**No es:** Inbox (interrupción), Session (un run), Ripples (grafo de causas).  
Hoy `task.activity[]` es log por task; Activity lo agrega.  
**Done when:** un `POST .../run` mock produce ≥1 fila en el feed sin abrir la session.  
**Non-goal:** telemetría comercial / ROI.

### Goals (`/goals`) — Fase 4

**Job:** trabajo abierto: spec → DoD aprobado → orquestador spawnea especialistas hasta checkboxes o rail.  
**No es:** Task grande ni Template de cadena fija.  
**Done when:** DoD 2 ítems → ≥2 sesiones; cap `0.00` rechaza spawn; sin `dodApproved` no hay spawn.  
**Non-goal:** goal sin spend cap por defecto.

### Skills (`/skills`) — Fase 3 (CRUD mínimo; strings en Phase 1)

**Job:** capacidad reutilizable `prompt` \| `file`, enganchada a varios agentes.  
**No es:** Agent ni MCP.  
Hoy `plan` declara `skills=("plan-mode",)` como string en seeds.  
**Done when:** quitar `plan-mode` del seed `plan` y el session manifest ya no la inyecta.  
**Non-goal:** marketplace de skills.

### Environment (`/environment`) — Fase 2

**Job:** segundo muro: red `open` \| `limited` + `allowedHosts[]`; env vars inyectadas al start (secret refs).  
**No es:** Connections (qué MCP/repo existe) — Environment dice qué red/env puede usar la sesión.  
**Done when:** `limited` a un host → runner no abre GitHub aunque el prompt lo pida.  
**Non-goal:** tokens en claro en la UI.

### Templates (`/templates`) — Fase 3

**Job:** receta que instancia una cadena de tasks; N+1 bloqueada hasta N `done`; gates en API.  
Seed: `compound-engineer-workflow` (9 pasos, `branchName`).  
**No es:** Goal (loop abierto).  
**Done when:** instantiate → 9 cards; token de agente no puede `PATCH done` en paso gated.  
**Non-goal:** inventar un segundo workflow de producto distinto al del walkthrough sin documentarlo.

### Knowledge (`/knowledge`) — Fase 2+ (wiki); RAG = Future

**Job:** corpus del operador que los agentes leen como verdad de producto (wiki / carpeta granted; luego RAG).  
**No es:** Files (blob crudo), Activity, ni Memory de usuario (Future).  
Orden: ACL filesystem → `librarian` escribe → RAG solo con Postgres + pipeline.  
**Done when:** agente sin grant de `/knowledge` no puede `fs.read` esa carpeta.  
**Non-goal:** pgvector en Phase 1–2.

### Ripples (`/ripples`) — Fase 5 (observabilidad de fan-out)

**Job:** grafo causa → efecto (“esto disparó aquello”).  
**No es:** Activity (timeline), Triggers UI sola, ni Session.  
Aristas típicas: webhook/cron → task+session; template step `done` → siguiente card; goal destroy → spawn; inbox reply → resume.  
**Done when:** instantiate de template muestra aristas step→step; webhook de prueba aparece como ripple.  
**Non-goal:** alias de Activity. Dominio público solo con webhooks.

### Connections (`/connections`) — Fase 2

**Job:** catálogo de lo que **existe** en el proyecto (MCP, repos, secret refs). El agente solo usa lo granted (default deny).  
Built-ins a documentar: AgentOS, Inbox, filesystem, GitHub. Front/Gmail = ejemplos, no vendors hardcodeados.  
**No es:** Environment (política de red).  
**Done when:** `plan` no puede invocar GitHub aunque la connection exista en el proyecto.  
**Non-goal:** OAuth tokens en la DB de la app.

### Admin (`/admin`) — Fase 1 copy → 2/6 config

**Job:** gobierno del **un** operador: tema, API base, runner mock|anthropic (claves solo `.env`), luego secret pointers, YAML push/pull, CLI token.  
**No es:** multi-tenant, billing, RBAC de equipo.  
**Done when (fase temprana):** Settings absorbido; sin formulario de API keys en el browser.  
**Non-goal:** miembros / Owner-Admin-Member estilo SaaS.

---

## Orden de construcción (no el del sidebar)

| Fase | Qué del sidebar se vuelve real |
|------|--------------------------------|
| 1 (hoy) | Inbox, Tasks, Agents, Sessions; Files/Settings placeholder |
| 2 | Environment, Connections, Files ACL |
| 3 | Templates + gates; Skills CRUD mínimo |
| 4 | Goals |
| 5 | Ripples deja de ser teórico (triggers/cron) |
| 6 | Admin: sync `agentos.yml` |
| 7 | Activity feed + live viewer; Knowledge wiki usable |

Hasta Fase 2, las entradas futuras en el nav solo deben existir como EmptyState o no existir en código.

---

## Criterio de “documentado de verdad”

Cada ítem de este archivo responde:

1. Job del operador  
2. Qué **no** es  
3. Fase en [ROADMAP.md](../ROADMAP.md)  
4. Dependencias  
5. Done when  
6. Non-goal  

Contrato API Phase 1 **no** crece aquí: [CONTRACT.md](../agentos/CONTRACT.md).
