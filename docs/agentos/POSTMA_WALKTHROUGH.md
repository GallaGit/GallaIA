# Walkthrough: lo que Danny Postma construyó (y cómo replicarlo)

Fuente: [How I Built My Own AgentOS on Claude's Agent SDK (So You Can Too)](https://youtu.be/Tos-zPxYPuc) — Danny Postma, 2026.

Este documento reconstruye **el sistema que enseñó en el video**, no su código de producción. Postma no publicó el repo. Los prompts, YAML y nombres de CLI aquí son **reconstruidos** (contrato de rol), no archivos literales. En código, cada prompt reconstruido debe llevar:

> Reconstructed from Danny Postma's AgentOS talk — not his verbatim prompt.

Blueprint de referencia (inglés, spec de implementación): [gist iannuttall/agentos-blueprint](https://gist.github.com/iannuttall/8152098b5ce8e6c1a7499ee561ed93f4).

GallaIA ya cubre un **MVP Phase 1** (Kanban + seeds + mock/stub). Este doc es el mapa completo de lo que él llegó a tener tras ~6 meses. No implementar Phase 2+ en el PR actual; ver [PHASE2_PLUS.md](PHASE2_PLUS.md).

---

## 0. Lo que hay que entender antes de copiar

Postma no “instaló AgentOS”. Lo construyó él, encima de Anthropic.

| Capa | Quién la posee | Qué hace |
|------|----------------|----------|
| **Control plane + UI** | Tú (GallaIA) | Proyectos, agentes, Kanban, goals, inbox, triggers, YAML, ACL |
| **Runtime** | Anthropic Managed Agents / Claude Agent SDK, o una VM barata | Contenedor efímero, tools, MCP, loop del agente |
| **Persistencia** | Tú | DB de dominio + Cloudflare R2 (archivos) + secretos cifrados |

El SDK ya da: sesiones, MCP, files API. AgentOS es **tu UI y tu política** encima: catálogo de agentes, least-privilege, Kanban, goals, inbox, cron, webhooks, routing de runners.

**No es un SaaS multi-tenant.** Es un sistema de un solo operador. Cada sesión es un contenedor desechable. El humano no vigila: el agente solo escribe al inbox cuando está atascado o necesita una decisión.

---

## 1. Lo que él hizo en 6 meses (historia del video)

Orden real, no el orden de implementación recomendado:

1. Trabajaba en la terminal de **Claude Code**. Tenía que quedarse mirando el portátil.
2. Quería **tirar trabajo y volver horas después** (cron, triggers, overload).
3. Encima del SDK de agentes gestionados de Anthropic, construyó un **control plane web**.
4. Aisló cada agente: un contenedor, unos MCP, unos repos, una red, unas carpetas. Default deny.
5. Como las sesiones mueren, montó un **filesystem persistente en Cloudflare R2** expuesto solo por un MCP con ACL.
6. Añadió Kanban, plantilla “compound engineer”, goals (gauntlet loop), inbox PWA, triggers y cron.
7. El cloud le salía caro (~500 USD/día anecdótico). Añadió una **VM Hetzner de ~10 USD** con Claude `--dangerously-skip-permissions` y Grok en yolo mode. Planners en cloud; workers locales/Grok.
8. En las últimas semanas el sistema **se construía y se operaba a sí mismo**. Dijo ~95% de su coding/ops automatizado.

Anecdotas (no son SLOs de producto): un goal sin cap de gasto llegó a ~1000 USD en una noche; un run de feature ~15:00–21:00 (5–6 h) y PR al día siguiente; un trigger de soporte disparó ~600 veces.

---

## 2. Recorrido de la demo (lo que enseñó en pantalla)

Orden aproximado del walkthrough de UI. Replica estas superficies.

### 2.1 Sidebar = “todos los aspectos”

App de un operador, desktop-first, inbox también en móvil (PWA + push):

1. Agents
2. Skills
3. Files (browser R2)
4. MCPs
5. Repos
6. Environment / env vars
7. Tasks (Kanban)
8. Goals
9. Inbox
10. Triggers
11. Automations (cron)
12. Sessions (live + historial)
13. Activity feed

### 2.2 Agents

Cada agente es un rol con **un solo trabajo**:

| Agente | Un trabajo |
|--------|------------|
| `default` | Caballo de batalla general |
| `plan` | Spec aprobada → plan de implementación. Escribe el plan. Termina. **No implementa.** |
| `spec` | Escribe spec detallada. **No puede marcar done** (approval gate). |
| `senior-dev` | Implementa / aplica fixes de review en el repo concedido. Commit. |
| `review-coordinator` | Spawnea reviewers, consolida must-fix / should-fix. No implementa. |
| `feasibility` | Review del plan: ¿es factible? |
| `scope-guardian` | Review del plan: ¿se infló el alcance? |
| `coherence` | Review del plan: ¿es coherente? |
| `implementation-plan-executioner` | Implementa el código según el plan. No relitiga el plan. |
| `librarian` | Actualiza la wiki interna según cómo funciona el código. No toca product code. |
| `customer-support` | Soporte inbound (p.ej. Front MCP). **Sin Gmail, sin GitHub, sin repo.** |
| `diagnostic` | Bug + chat de soporte + repo → informe de causa. No implementa hasta OK humano. |
| `linkedin-content` | Contenido recurrente. |

Campos por agente: prompt fundacional (compartido) + prompt de rol, modelo, skills, MCPs, repos, grants de filesystem, lista de colaboración (a quién puede spawnear), environment, preferencia de runner (`cloud` | `local` | `inherit`), acceso a inbox.

**Default deny.** Si no está listado, el agente no lo tiene. Un leak de prompt no debe poder llegar a GitHub si no se le dio GitHub.

Ejemplos que él subrayó:

- Plan agent: skill `plan-mode` + AgentOS MCP. **Sin** Ahrefs, **sin** GitHub.
- Support bot: Front (o equivalente). **Nunca** Gmail. **Nunca** codebase.

### 2.3 Skills

Capacidad reutilizable, no un agente. Ejemplo: `plan-mode` (`/plan`) = prompt + scripts auxiliares. Se engancha a varios agentes. Puede ser `prompt` o `file` (script en el filesystem).

### 2.4 Filesystem (R2 + MCP)

Las sesiones son efímeras → no hay disco del contenedor que sobreviva.

- Blobs en **Cloudflare R2**.
- Agentes **nunca** tocan R2 directo. Solo el **filesystem MCP**.
- Tools mínimas: `fs.list`, `fs.read`, `fs.write`, `fs.delete`, `fs.mkdir`.
- ACL en servidor: `canRead` / `canWrite` / `canDelete` por prefijo de carpeta. Poder escribir no implica poder borrar.
- Convención: `/agents/{slug}/` por agente; `/goals/{goalId}/` compartido en un goal.
- UI: listar, abrir, editar, descargar, preview.

Sin esto, un agente con filesystem “ilimitado” te limpia el disco. Por eso existe.

### 2.5 MCPs y secretos

Conexiones nombradas (`github`, `front`, `agentos`, `r2-fs`, `inbox`, …). El token **no** vive en la DB de la app: referencia a **Google Secret Manager / Cloud KMS** (él no recordó el nombre exacto del producto). Se inyecta al arrancar la sesión.

MCPs que **tú** implementas:

| MCP | Para qué |
|-----|----------|
| **AgentOS** | Leer/escribir la task, marcar status (excepto si hay approval gate), spawnear colaborador, leer metadata permitida |
| **Inbox** | Mensaje al humano, pregunta de opción múltiple, leer respuestas |
| **R2 filesystem** | Archivos con ACL |
| **GitHub** | Solo si el agente tiene esa conexión + repo |

Otros (Front, Ahrefs, Gmail, Mongo read-only) son **ejemplos configurables**, no lógica hardcodeada.

### 2.6 Environment / red

Independiente de los MCP:

- `open` o `limited` + `allowedHosts[]` (ej. `api.front.com`).
- Si es `limited`, el proxy **bloquea el resto a nivel de red**, incluido GitHub, aunque un prompt leak lo pida.

Dos muros: grants de MCP + deny de red.

### 2.7 Tasks (Kanban)

Columnas: **todo → doing → review → done**.

Al crear una task:

- nombre, descripción, attachments
- asignar un agente (o humano)
- run: ahora | datetime | cron (ej. cada lunes del mes, resumir inbox)
- opcional: partir de una plantilla

**Approval gate:** el agente puede llevar la card a `review`. La API **rechaza** `status=done` con token de sesión del agente. Solo el humano marca `done`. La siguiente task de la cadena no arranca hasta entonces.

Usado en: aprobación de spec, y review humano del PR final.

### 2.8 Plantilla “compound engineer” (feature build)

Él la describió como ~3 h fully managed; un run concreto duró ~5–6 h. El 99% funciona porque **hay E2E dentro del workflow**. Variable típica: `branchName`.

Instanciar la plantilla crea una **cadena** de 9 tasks. La N+1 está bloqueada hasta que la N está `done`.

| # | Paso | Agente | Gate |
|---|------|--------|------|
| 1 | Escribir spec | `spec` | **sí** (humano aprueba) |
| 2 | Plan | `plan` | no (avisa por inbox/activity) |
| 3 | Plan review | `review-coordinator` | no — spawnea 4 reviewers (nombró feasibility, scope-guardian, coherence; el cuarto no lo nombró → en réplicas se usa un `plan-risk` reconstruido) |
| 4 | Revisar plan | `plan` | no |
| 5 | Implementación + E2E | `implementation-plan-executioner` | no |
| 6 | Code review | `review-coordinator` | no |
| 7 | Aplicar fixes | `senior-dev` | no |
| 8 | Wiki | `librarian` | no |
| 9 | Review humano del PR | `human` | **sí** — merge |

Cadena de **bug report** (después de OK humano): implement → plan → plan review → fix → E2E → humano merge. Mismos agentes.

### 2.9 Goals / “gauntlet loop”

Para trabajo abierto (no una cadena fija). Flujo diario que describió:

1. Por la mañana escribe un spec.
2. Lo tira al sistema de goals.
3. El sistema redacta **Definition of Done** (checkboxes).
4. Él **aprueba el DoD**. Sin eso no arranca.
5. Corre 5–6 horas. Él hace otra cosa.
6. Al final del día: PR. Review, merge, al día siguiente otro.

Después de **cada** sesión, un **orquestador** (código del control plane, no un chat agent):

- lee progress log, DoD, resumen de la sesión
- marca checkboxes cumplidos
- si todo cumplido → `completed`
- si un rail salta → `stopped-*`
- si no → spawnea el siguiente especialista

Rails (obligatorios):

| Rail | Default / comportamiento |
|------|--------------------------|
| Spend cap | UX difícil de olvidar. Sin cap solo con confirmación explícita. |
| Max wall time | Para el loop |
| Stuck | ~19 iteraciones iguales (mismo especialista + mismo DoD sin progreso) → stop |

Estado compartido: progress log append-only, inbox del goal, carpeta R2 del goal.

Routing: “si cloud está ocupado, local; si no, cloud”. Override por goal: “este solo en local”. Planners (él: Fable/Claude cloud); workers (Grok 4.6, rápido) en local.

### 2.10 Inbox + PWA

Único canal de interrupción humana. No hay Slack paralelo.

- Texto o pregunta con radio buttons (estilo ask-user-question de Claude).
- Responder **reanuda** la sesión en `waiting-inbox`.
- El agente **no** spamea progreso rutinario. Eso va al activity de la task.
- PWA instalable, push cuando algo está done o necesita ayuda.

### 2.11 Triggers y automations

**Trigger:** webhook público + secreto → task/sesión del agente scoped.

Seeds de ejemplo:

1. Support inbound → `customer-support` con Front only → asigna rep/AE.
2. Bug report → `diagnostic` con repo + chat → informe. Si el humano aprueba, arranca la cadena de fix + E2E.

**Automation:** cron nombrado en el sidebar (LinkedIn semanal / primer día de mes). Distinto de “task recurrente” (campo schedule en una task). Mismo scheduler por debajo.

### 2.12 Sessions + activity

- Viewer en vivo: tool calls mientras `running`.
- Log persistido en la Session para replay.
- Feed global de acciones / inbox / transiciones de Kanban.

### 2.13 YAML + CLI

Cada proyecto tiene un `agentos.yml` que **imita la UI**: agentes, skills, templates, MCP, repos, prompts.

Comandos que nombró:

| Comando | Qué hace |
|---------|----------|
| `agentos help` | usage |
| `agentos push` / `pull` | YAML ↔ control plane |
| `agentos project create` | proyecto |
| `agentos goal create` | goal (después de brainstorm local en Claude) |
| `agentos task create` | task; aplica agentes del YAML/template |
| `agentos agent update` | ajustar agentes |
| `agentos skill create` | skill nueva |

Patrón de uso: brainstorm en Claude local → cuando está listo, la CLI crea el goal/task en AgentOS. AgentOS es el sistema de registro. Auth CLI = token personal.

---

## 3. Ciclo de vida de una sesión (el corazón del sistema)

Implementar esta máquina de estados **tal cual**:

```
requested
  → provisionar contenedor (Managed Agents / SDK / slot local)
  → inyectar env desde secret store (solo keys listadas)
  → adjuntar MCPs permitidos
  → aplicar policy de red del environment
  → clonar cada repo concedido en mountPath
  → montar filesystem MCP con ACL de ese agente
  → inyectar prompt fundacional + rol + skills
  → status=running
  → el agente trabaja (tool calls → live viewer + activity)
  → si pregunta inbox: waiting-inbox; al responder, resume
  → si termina y no hay gate: AgentOS MCP marca done/review
  → si git-write: commit, guardar sha
  → cleanup
  → destruir contenedor
  → status=destroyed
```

Reglas:

- Tras destroy no queda nada del contenedor salvo **commits git** y **writes R2 vía MCP**.
- La siguiente sesión clona/pull otra vez. No hay workspace sucio “caliente”.
- Un fallo también destruye el contenedor. Antes: persistir logs y tool-call history.
- En goals: tras destroy corre el orquestador y puede encolar la siguiente sesión.

---

## 4. Paso a paso para construir lo mismo

No empieces por goals ni por la VM de 10 USD. Él llegó ahí al final. El orden de **construcción** (aceptación de cada fase) es este. En GallaIA el stack es FastAPI + React + SQLite (Postgres después), no el TypeScript del gist. El **contrato de producto** sí es el mismo.

### Fase 0 — Esqueleto

1. Auth de un solo usuario.
2. Shell de UI con las rutas del sidebar (pueden 404).
3. Stub CLI `agentos help`.

**Done when:** app abre, sidebar existe, API health ok.

### Fase 1 — Un agente, una task, una sesión

Esto es lo que GallaIA ya aproxima (mock + stub Messages, no Agent SDK completo).

1. CRUD Project / Agent / Task.
2. Seeds: `default`, `plan`, `senior-dev` (prompts reconstruidos, etiquetados).
3. Kanban: crear task, asignar, **Ejecutar ahora**.
4. Runner: crear sesión, adjuntar AgentOS MCP + Inbox MCP, correr, destruir.
5. El agente actualiza la task **por el MCP**, no “porque el backend lo adivinó”.
6. Session con log básico de tool-calls.

**Done when:** creas una task → arranca sesión → el agente marca la card vía MCP → el contenedor/sesión se destruye → card `done`.

Runtime real (cuando toque sustituir el stub):

- Cloud: [Claude Managed Agents](https://platform.claude.com/docs/en/managed-agents/sessions) (beta `managed-agents-2026-04-01`) o [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/).
- Local: worker en VM Linux (no Mac-only) que ejecute Claude Code con skip-permissions / Grok yolo, detrás de la misma interfaz `provision / streamToolCalls / injectReply / destroy`.

### Fase 2 — Isolation (lo más importante y lo más difícil)

1. Default deny en el **session manifest**.
2. Grants por agente: MCP, repo, env, filesystem, collaboration list.
3. Network `open` | `limited` + allowlist en el proxy del runner.
4. R2 + filesystem MCP con ACL server-side (`canRead`/`canWrite`/`canDelete`, path prefix, deny `../`).
5. Secret refs; inyección solo al start; DB solo guarda el puntero.
6. File browser en UI.

**Done when:**

- Un agente “support” con un Front fake **no** puede llamar GitHub ni leer `/agents/otro/`.
- Un `plan` **no** puede usar un GitHub que existe en el proyecto pero no está granted.
- Delete sin `canDelete` → deny.

### Fase 3 — Templates, gates, cadenas, schedule

1. `TaskTemplate` + instantiate.
2. Approval gates en API **y** MCP (no honor system).
3. Scheduler de follow-ups.
4. Seed `compound-engineer-workflow` (9 pasos).
5. Run at + cron en tasks.

**Done when:** instanciar la plantilla crea 9 cards; el paso 2 no arranca hasta que un humano marca el 1 `done`; un token de agente no puede marcar el 1 `done`.

### Fase 4 — Goals

1. Goal + generar/aprobar DoD + progress log.
2. Orquestador después de cada sesión.
3. Spend cap, max time, stuck=19.
4. `runnerPreference` por goal.

**Done when:** un goal con 2 ítems de DoD termina con ≥2 sesiones de especialistas; stuckThreshold=2 para tras 2 iteraciones sin progreso; cap 0.00 USD rechaza spawn.

### Fase 5 — Triggers + automations

1. Webhook + secreto (HMAC). Payload sanitizado (sin headers/secrets crudos al prompt).
2. Seeds: support-inbound, bug-report.
3. Tras OK humano en bug: cadena fix + E2E.
4. Cron nombrados.

**Done when:** secreto malo → 401; bueno → task+sesión; un cron dispara en un reloj de test.

### Fase 6 — YAML / CLI

1. Schema `agentos.yml` = proyección de la UI.
2. `push` / `pull` / `project create` / `goal create` / `task create` / agent update / `skill create`.

**Done when:** un YAML pusheado produce los mismos agentes+template que ves en la UI; `pull` tras `push` es identidad (salvo whitespace).

### Fase 7 — PWA, live viewer, routing local

1. Inbox PWA + web push.
2. Radio buttons; reply reanuda sesión.
3. Live viewer (SSE/websocket).
4. Activity feed.
5. Worker local + routing (planners cloud, workers local).

**Done when:** `inbox.ask` se ve en viewport de móvil; responder reanuda; un planner va a cloud y un worker se puede forzar a local.

---

## 5. Cómo se usa el sistema (operador), no cómo se codea

Esto es lo que él **hace ahora** un día típico:

1. Escribe un spec (lista de “esto tiene que pasar”).
2. `agentos goal create` (o lo pega en la UI de Goals).
3. Revisa y aprueba el Definition of Done.
4. Se va. El orquestador spawnea especialistas 5–6 h.
5. Si un agente se atasca: push en el teléfono → radio / texto → la sesión sigue.
6. Por la tarde: PR. Review. Merge.
7. Triggers de soporte y crons de contenido corren solos, con agentes **walled**.

Para una feature con calidad de “equipo”:

1. Instanciar `compound-engineer-workflow`.
2. Aprobar la spec (gate).
3. Dejar que plan → 4 reviewers → revise → implement+E2E → review → fixes → librarian.
4. Merge humano (gate).

---

## 6. Least-privilege (requisitos, no sugerencias)

1. Default deny.
2. Un contenedor por sesión. Nunca un writable compartido entre agentes.
3. Support: Front sí; Gmail no; GitHub/repo no.
4. Plan: plan-mode + AgentOS MCP; Ahrefs/GitHub no.
5. Allowlist de red = segundo muro.
6. Filesystem = MCP, no disco superuser. Write ≠ delete.
7. Grants de carpeta por agente (otro agente puede tener read-only sobre la tuya).
8. Secretos inyectados solo si están listados. Cifrados fuera de la app DB.
9. Approval gates en API, no en el prompt.
10. Collaboration list = único path de spawn.
11. Diseña como si el modelo **fuera a usar todas las tools que le diste**.

---

## 7. Qué GallaIA ya tiene vs qué falta

| Pieza del video | GallaIA hoy |
|-----------------|-------------|
| Seeds `default` / `plan` / `senior-dev` | Sí (prompts reconstruidos) |
| Kanban todo/doing/review/done + run now | Sí |
| Session + tool log | Sí (mock / stub Messages) |
| Inbox list + reply stub | Parcial |
| Claude Agent SDK / Managed Agents + destroy container | No (stub Messages, no harness) |
| Isolation ACL + red + R2 MCP | No (Phase 2+) |
| Template 9 pasos + gates reales | No |
| Goals + orquestador + rails | No |
| Triggers / cron | No |
| YAML CLI | No |
| PWA push + live SSE | No |
| Runner Hetzner / Grok | No; y **no** Mac-only ni Cursor Cloud Agents |

Detalle de producto local: [AGENTOS.md](../product/AGENTOS.md). Contrato API actual: [CONTRACT.md](CONTRACT.md).

---

## 8. Lo que no debes copiar / no inventar

| Ítem | Estado |
|------|--------|
| Prompts literales de Postma | Desconocidos. Reconstruir contratos y etiquetarlos. |
| Nombre exacto del producto Google de secretos | Él lo olvidó. Secret Manager o Cloud KMS. |
| Su runner custom futuro | Mencionó que lo estaba pensando. No es spec. SDK + VM local basta. |
| Cuarto reviewer del plan | Dijo “cuatro”, nombró tres. Añadir `plan-risk` reconstruido. |
| Harness E2E propio | “E2E está dentro del workflow”: correr el E2E **del repo**, no inventar un framework. |
| Repo `fight-for` | Ejemplo de mount, no producto. |
| Costes 500/día, 1000/noche, VM 10 USD | Anécdotas que motivan routing y caps. |
| Multi-user, billing, SaaS | No lo describió. Un operador. |
| Electron / Tauri / solo Mac | Explicitamente **no** es el camino de GallaIA. |

---

## 9. Tests de aceptación (cuando se implemente de verdad)

Automatizados:

1. Tras un run, no queda handle de runner; la siguiente task reclona, no reusa workspace sucio.
2. ACL fs: write/delete/`../` denegados sin grant.
3. Agente sin GitHub no puede invocar tools de GitHub aunque el proyecto las tenga.
4. Environment limited a `api.front.com` no abre `github.com`.
5. Gate: token de agente `PATCH done` → 403; humano → 200.
6. Template: 9 tasks, orden, `branchName` interpolado.
7. Inbox resume: `waiting-inbox` + reply → continúa con la respuesta.
8. Multiple-choice guarda `selectedChoiceId`.
9. Rails de goal: spend / time / 19 stuck → `stopped-*`.
10. Goal no spawnea sin `dodApproved`.
11. Webhook: secreto malo 401; bueno task+sesión.
12. YAML round-trip push/pull.
13. Fixture support: manifest de sesión **sin** GitHub, Gmail, clone de repo.
14. Orquestador no spawnea un agente fuera de la collaboration list.

Demo manual (humano): spec → goal → aprobar DoD → irse → PR o inbox real; POST de soporte fake; push en el teléfono y responder un radio.

---

## 10. Relación con `galladev.com`

El dominio **no forma parte** de lo que Postma enseñó como núcleo. Él necesitaba:

- HTTPS público **cuando** hay webhooks y PWA push.
- Nada de eso bloquea Fases 0–1 en localhost.

Cuando existan triggers (Fase 5) y PWA (Fase 7), ahí sí: `app.galladev.com` + TLS + DNS. Hasta entonces, renovar el dominio basta.
