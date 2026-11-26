# Especificación UI — Árbol de agentes GallaIA

**Estado:** propuesta / borrador (26 de noviembre de 2026, Europe/Berlin). No está implementado. Pendiente de decisión de Ociel.  
**Tipo:** especificación de rediseño. No es implementación.  
**Referencia visual:** estilo «Multi-Agent Workspace» (tema oscuro).  
**Base técnica:** `master` de `GallaGit/GallaIA` en `14b4983` (PR #54 fusionado). Frontend React 19 + Vite + React Router 7; backend FastAPI.  
**Regla de oro:** no inventar datos. Si un elemento de la plantilla no tiene API, se marca como *placeholder* o *fase posterior*.

**Paleta:** provisional. Navy de la plantilla (`#070B14`, `#10182A`) + burdeos GallaDev `#7A1F2B` como acento + crema `#F5F0E8` para destacados. Ver pregunta 1.

### Boceto

- [Captura del HTML animado](boceto/boceto.png) (escritorio 1920×1080)
- [HTML animado](boceto/boceto-animado.html) (abrir en el navegador)
- [Vídeo de 4 s](boceto/boceto-animado.mp4)
- Capturas de Stitch: [pantalla principal](boceto/pantalla-principal-stitch.png), [FE seleccionado con aprobación pendiente](boceto/variante-fe-seleccionado.png)
- Proyecto Stitch: [GallaIA - Workspace de agentes](https://stitch.withgoogle.com/projects/15634621524618899645) (**privado**; hace falta la cuenta del propietario para abrirlo)

Las capturas de Stitch son un primer render y pueden incluir métricas o rutas de ejemplo que **no existen** en el backend (por ejemplo un % de progreso o ficheros inventados). El HTML animado se ajusta a esta especificación.

### Preguntas abiertas para Ociel

1. **Paleta:** ¿seguimos el navy de la plantilla, la marca grafito `#202124` / burdeos `#7A1F2B` / crema `#F5F0E8`, o un híbrido (navy + burdeos del Orquestador)? ¿El tema claro se mantiene como alternativa?
2. **Prompt en las tarjetas FE/BE:** hoy todo sale hacia el Orquestador. ¿Lo dejamos así en el MVP, o quieres poder escribirle directo a FE o a BE?
3. **Inbox:** ¿confirmas que la vista nueva prioriza las aprobaciones de delegación (F2.2c) y deja los handoffs de tareas/sesiones como sección secundaria?

---

## 1. Objetivo

Sustituir la UI actual (listas y páginas sueltas con estética «atelier», tema claro canónico) por un espacio de trabajo único, oscuro, centrado en el árbol de los 3 agentes: **Orquestador** (raíz), **FE** y **BE** (hijos). El operador (Ociel) ve el equipo, habla con el Orquestador, sigue las delegaciones y aprueba lo que el grafo deje en espera.

Fuera de alcance de este documento: código, ramas, PRs, nuevos agentes y la integración GallaIA ↔ GDW.

---

## 2. Qué hay hoy (para no perderlo)

La app actual vive en `frontend/src`: `Layout` (sidebar + toggle claro/oscuro), páginas Agentes, Conversaciones, Tareas, Sesiones, Inbox, Activity, Live, y placeholders de Archivos y Ajustes. «Registrar agente» está deshabilitado y debe seguir así.

Hay **dos planos de API** y la UI no los usa por igual:

| Plano | Prefijo | Lo que ya consume el frontend |
|---|---|---|
| AgentOS (en memoria) | `/api/v1/agentos` | agentes, tareas kanban, sesiones, inbox de handoffs, `run` |
| Control plane (SQLAlchemy) | `/api/v1` | hilos, mensajes, SSE, delegaciones, activity, ruta del runner |

**Huecos importantes de la UI actual:** no llama a `GET /api/v1/inbox` ni a `POST /inbox/{id}/decide` (F2.2c), ni a `GET /threads/{id}/graph-state`, ni a `GET /projects`. El «estado» healthy/degraded/offline de las tarjetas de agente es local: el backend no lo envía y casi siempre cae en `healthy`.

Autenticación ya resuelta: token de operador en `Authorization: Bearer`, guardado en `sessionStorage`; el SSE va por `fetch` (nunca el token en la URL). Eso se mantiene.

---

## 3. Layout y regiones

Escritorio (≥1280px), cuatro zonas fijas más una barra inferior:

```
┌──────────┬────────────────────────────────────┬──────────────────┐
│ Sidebar  │ Cabecera del proyecto              │                  │
│          ├────────────────────────────────────┤  Panel derecho   │
│          │ Lienzo: árbol de agentes           │  del agente      │
│          ├──────────────────┬─────────────────┤  seleccionado    │
│          │ Dependencies &   │ Quick Actions   │                  │
│          │ Flow             │                 │                  │
├──────────┴──────────────────┴─────────────────┴──────────────────┤
│ Pestañas inferiores de agentes abiertos                          │
└──────────────────────────────────────────────────────────────────┘
```

- **Sidebar (~240px):** marca GallaIA; nav; contadores de estado; pie con proyecto actual.
- **Cabecera:** nombre del proyecto, badge «Activo», conteos, acciones y vista.
- **Lienzo central:** tarjeta del Orquestador arriba, conectada a FE y BE. Debajo, el grafo de dependencias del hilo activo y las acciones rápidas.
- **Panel derecho (~360px):** detalle del agente (o del hilo) seleccionado.
- **Barra inferior:** pestañas de agentes abiertos en esta sesión de UI (estado local, sin API nueva).

Las rutas actuales (`/threads`, `/tasks`, `/inbox`, `/sessions`, etc.) no se eliminan: pasan a ser vistas internas o destinos del nav. La home nueva es el árbol (`/` o `/agents`).

---

## 4. Mapeo plantilla → GallaIA

### 4.1 Sidebar

| Plantilla | En GallaIA | Datos | Notas |
|---|---|---|---|
| Agents | Árbol (home) | `GET /api/v1/agentos/agents` (o control plane `GET /api/v1/agents`) | Solo `orquestador`, `fe`, `be`. |
| Threads | Conversaciones | `GET /api/v1/threads` | Ya existe la página. |
| Worktrees | Worktrees | — | **Fase posterior.** Ítem visible, deshabilitado, texto «Próximamente». |
| Project | Proyecto | `GET /api/v1/projects` | Hoy el seed se llama `default`. Mostrar `name` + `slug`. Sin selector de rama. |
| File Explorer | Archivos | — | Ya es placeholder. `GET /agents/{id}/fs` es una **ACL de raíces**, no un explorador de ficheros. En una fase media se puede mostrar esa ACL como «Permisos de FS». El árbol de archivos es **fase posterior**. |
| Search | Buscar | — | MVP: filtro local de hilos y agentes. Búsqueda en servidor: **fase posterior**. |
| Settings | Ajustes | Parcial | Hoy es placeholder. Fase 3: tema, campo del token de operador (sin mostrarlo una vez guardado), runner de solo lectura (`GET /runners/route`). Secretos: nunca listar valores. |
| Running / Waiting / Blocked / Completed / Paused | Contadores | Derivados (ver §5) | No hay endpoint de resumen. Se calculan en el cliente. No inventar un total si no hay fuente. |
| Current project / branch (pie) | Proyecto actual | `GET /projects` | Rama git: **placeholder** («rama: no disponible»). |

### 4.2 Cabecera

| Plantilla | En GallaIA |
|---|---|
| Nombre del proyecto | `projects[].name` (proyecto `default` si no hay otro). |
| Badge Active | «Activo» si hay un hilo `open` con stream SSE en curso o una sesión `running`/`starting`. Si no, «En reposo». |
| Conteos (agentes, worktrees, estados) | Agentes: siempre 3. Worktrees: «—» o oculto. Estados: §5. |
| Create Agent | El botón actual **sigue deshabilitado** («Registrar agente · Próximamente»). No hay alta de agentes en v2. |
| View | Alternar árbol (nuevo) y lista (cuadricula actual de Agentes). |

### 4.3 Tarjetas del árbol

El árbol es **fijo de 2 niveles**: Orquestador arriba; FE y BE al mismo nivel, unidos por líneas al raíz. No hay nietos. No se pueden añadir nodos.

Campos de cada tarjeta:

| Campo de la plantilla | Orquestador | FE / BE |
|---|---|---|
| Nombre y rol | `title` + `one_job` | igual |
| Badge de estado | Estado derivado del agente (§5) | igual |
| Descripción | `one_job` (o un recorte de `role_prompt`) | igual |
| Nº de sub-agentes | `2` (FE y BE; sale de `collaboration` del seed) | `0` |
| Worktree / branch | Placeholder | Placeholder |
| Progress % | **No hay campo en el backend.** Opcional en fase 3: aproximación `tareas done / total` del agente. Si no hay tareas, no se pinta un 0 % falso: se oculta. | igual |
| Input de prompt | Caja real: crea o usa un hilo abierto y hace `POST /threads/{id}/messages` con `sender=user`, `recipient=orquestador`, `kind=text`. Si «auto-avance» está on, abre el SSE como hoy. | En el MVP **no envía al especialista**. El texto se manda al Orquestador pidiendo trabajo para FE o BE (misma regla de negocio: solo Orquestador o el usuario pueden delegar). Un prompt directo al especialista es pregunta abierta (§11). |

Colores de acento (solo borde/halo, no datos): Orquestador burdeos, FE cian, BE verde.

### 4.4 Dependencies & Flow + Quick Actions

El diagrama rico de la plantilla (Architecture → QA → Build/Run → Test Results) **no existe** en GallaIA. No se reproduce.

En su lugar, el panel inferior izquierdo reutiliza `GET /api/v1/threads/{id}/delegations` del hilo activo:

- Nodos fijos: `user`, `orquestador`, `fe`, `be`.
- Aristas: `source → target`, `brief`, `status: pending | answered`.
- Si hay `summary_id`, se marca «Resumen enviado al usuario».
- Complemento (fase 2): `GET /threads/{id}/graph-state` para `pending_approval` (id de Inbox) y el motor (`langgraph` / clásico).

Si no hay hilo seleccionado: estado vacío («Elige o crea un hilo»).

**Quick Actions** (solo acciones con API real; el resto deshabilitado):

| Acción | API / comportamiento |
|---|---|
| Crear hilo | `POST /api/v1/threads` |
| Enviar al Orquestador | `POST /threads/{id}/messages` |
| Avanzar | abre `GET /threads/{id}/stream` (como hoy) |
| Cerrar hilo | `PATCH /threads/{id}` `{status: closed}` |
| Aprobar / Rechazar | `POST /api/v1/inbox/{id}/decide` (F2.2c), visible solo si hay aprobación pendiente |
| Crear worktree / Pausar todo / Cambiar rama | **Fase posterior**, botones deshabilitados |

### 4.5 Panel derecho (agente seleccionado)

Pestañas de la plantilla:

| Tab | MVP | Datos reales | Aplazamiento |
|---|---|---|---|
| **Chat** | Sí | Mensajes del hilo activo (`GET /threads/{id}` + SSE). Se destacan los que tienen al agente como `sender` o `recipient`. Caja de prompt, «Avanzar», «Cerrar hilo», toggle auto-avance (ya en `localStorage`). | — |
| **Context** | Sí (fase 3 o junto al MVP si cabe) | `one_job`, modelo, skills, `runner_preference`, prompts de fundación y rol (solo lectura). | — |
| **Worktree** | Placeholder | — | **Fase posterior.** |
| **Files** | Placeholder | ACL en fase 3: `GET /api/v1/agents/{id}/fs` o `/agentos/agents/{name}/fs`. | Explorador de ficheros: **fase posterior**. |
| **Tests** | Placeholder | No hay resultados de test por agente. `tool_events` de una sesión no se presentará como «suite de tests». | **Fase posterior.** |
| **Settings** | Fase 3, solo lectura | Grants y red (`GET .../grants`, `.../network`), modelo, runner. Uso de LLM: `GET /api/v1/llm/usage` (ya no incluye prompts ni claves). | Edición de grants/red y cualquier secreto: fuera de este rediseño. **Nunca mostrar valores de secretos** (`GET .../secrets` no se pinta). |

Bloques extra de la plantilla en el panel:

- **Progreso de tarea:** si el agente tiene una tarea `doing` o `review` (`GET /agentos/tasks`), mostrar nombre y estado kanban. Sin barra de % inventada.
- **Sub-agents:** solo en Orquestador, lista estática FE y BE. «Create Sub-agent» deshabilitado.
- **Dependencies:** las aristas de delegación que tocan a ese agente.
- **Worktree / Change Branch:** placeholder.

### 4.6 Pestañas inferiores

Estado puramente de cliente: al seleccionar un agente se abre una pestaña (máximo las 3). Cerrar la pestaña no borra nada en el servidor. Si no hay ninguna, no se muestra la barra.

---

## 5. Estados (plantilla → datos reales)

La plantilla usa Running / Waiting / Blocked / Completed / Paused. GallaIA no tiene esos cinco valores en un solo campo. Se **derivan** en el cliente. Si no hay evidencia, el contador queda en 0; no se rellena con «healthy» por defecto.

Fuentes: hilo `open|closed`; delegación `pending|answered`; Inbox de control plane `open|answered` con `kind=thread_approval`; `graph-state.pending_approval`; tarea `todo|doing|review|done`; sesión `starting|running|destroyed` (y fallos si el runner los deja); flag local «en directo» del SSE.

| Badge de la plantilla | Cuándo se usa en GallaIA |
|---|---|
| **Running** | Stream SSE abierto en un hilo, o sesión `starting`/`running`, o tarea `doing` asignada a ese agente. |
| **Waiting** (espera de aprobación) | Inbox de control plane `open` + `kind=thread_approval`, o `graph-state.pending_approval != null`. En el árbol, el badge va al especialista destino de esa delegación y un aviso en el Orquestador. |
| **Paused** | **No existe un pause en la API.** El interrupt de LangGraph (F2.2c) es el mismo hecho que Waiting. En el MVP, Paused se omite o se muestra fijo en 0, con nota «reservado». No duplicar el mismo ítem en Waiting y Paused. |
| **Blocked** | Solo con fallo explícito (sesión fallida, o rechazo ya registrado que deje trabajo sin cerrar). Una delegación `pending` **sin** aprobación humana no es «bloqueado»: es trabajo en curso o Waiting. |
| **Completed** | Hilo `closed`, o delegación `answered`, o tarea `done`. En contadores globales: nº de hilos cerrados (y, si se enseña desglose, tareas `done`). |
| *(implícito) En reposo* | Agente sin hilo/sesión/tarea activa. No aparece en la plantilla; es el estado por defecto de FE/BE al arrancar. |

El Inbox de AgentOS (`kind: session|task`, estados tipo `waiting-inbox` / `review`) es **otro buzón**. En este rediseño el Inbox del nav prioriza las aprobaciones F2.2c del control plane. Los handoffs AgentOS pueden quedar como sección secundaria de la misma vista, sin mezclar los modelos.

Requisito: `GALLAIA_THREAD_APPROVAL=true` y motor LangGraph para que Waiting tenga sentido. Si el flag está apagado, el contador Waiting queda en 0 y no se muestran botones de decidir.

---

## 6. Interacciones principales

1. Cargar home → proyectos, 3 agentes, lista de hilos, inbox abierto (`status=open`). Pintar árbol.
2. Clic en una tarjeta → selección, abre pestaña inferior y rellena el panel derecho (Chat del hilo activo, o vacío con «Crear hilo»).
3. Prompt en la tarjeta del Orquestador o en el Chat → mensaje al Orquestador; auto-avance opcional dispara el SSE.
4. El grafo inferior se refresca al terminar el stream (igual que hoy el panel «Delegaciones»).
5. Si aparece `pending_approval`, el badge Waiting se enciende y Quick Actions / Chat muestran Aprobar o Rechazar (cuerpo `{approved, note}`). Tras decidir, se refrescan inbox, grafo y mensajes.
6. «Cerrar hilo» deshabilita prompt, avance y stream, como ahora (409 si el hilo ya está cerrado).
7. Errores de API: el patrón actual («API no disponible» / mensaje del backend). El token no se imprime. Un 401 limpia `sessionStorage` y vuelve a pedir el token, como hoy.

---

## 7. Fuentes de datos y endpoints nuevos

**Ya existen y bastan para el MVP y la fase de aprobaciones:**

- `GET /api/v1/projects`
- `GET /api/v1/agentos/agents` y `GET /api/v1/agentos/agents/{name}` (el frontend ya los usa)
- `GET/POST /api/v1/threads`, `GET /threads/{id}`, `POST /threads/{id}/messages`, `POST /threads/{id}/advance`, `GET /threads/{id}/delegations`, `GET /threads/{id}/graph-state`, `GET /threads/{id}/stream`, `PATCH /threads/{id}`
- `GET /api/v1/inbox?status=open`, `POST /api/v1/inbox/{id}/decide`
- `GET /api/v1/agentos/tasks`, `GET /api/v1/agentos/sessions`, `GET /api/v1/activity`
- `GET /api/v1/runners/route`, `GET /api/v1/llm/usage`
- Grants / red / ACL de FS (fase 3, solo lectura)

**No hacer un endpoint nuevo** de «workspace summary» en el MVP: los conteos se agregan en el cliente. Se puede proponer más adelante si el coste de N llamadas se nota.

**Endpoints que habría que crear (fase posterior, no bloquear el rediseño):** worktrees y rama git, listado real de ficheros, resultados de tests por agente, búsqueda en servidor, pausar/reanudar, alta de agentes, un `%` de progreso de primera clase.

Cuerpos de mensajes: el backend ya recorta/rechaza por encima de 20 000 caracteres (SEC-009). La UI debe respetar ese tope y no volcar contenido no confiable sin el encuadre habitual.

---

## 8. Tokens de diseño (tema oscuro)

La plantilla es oscura, densa, con tarjetas de borde de color y fondo navy. La UI actual es «atelier» clara (`#F7F3EB`, índigo `#3730A3`, coral `#E11D48`) y el modo oscuro solo invierte a piedra cálida. Este rediseño **pasa a oscuro por defecto**. El toggle claro se puede conservar, usando la paleta atelier ya definida para el tema light.

**Propuesta canónica (alineada a la plantilla):**

| Token | Valor | Uso |
|---|---|---|
| `--bg` | `#070B14` | Fondo del lienzo |
| `--bg-elevated` | `#10182A` | Sidebar, cabecera, panel derecho |
| `--bg-card` | `#162036` | Tarjetas |
| `--line` | `#243049` | Bordes |
| `--ink` | `#E8EEF8` | Texto |
| `--ink-muted` | `#8B9BB4` | Secundario |
| `--accent` | `#3B82F6` | Botón primario, foco |
| `--orq` | `#9B2C3A` | Acento Orquestador |
| `--fe` | `#22D3EE` | Acento FE |
| `--be` | `#34D399` | Acento BE |
| `--ok` | `#34D399` | Completed / answered |
| `--warn` | `#FBBF24` | Waiting |
| `--danger` | `#F43F5E` | Blocked / error |
| `--run` | `#60A5FA` | Running |
| Radio | 12–16px | Tarjetas; inputs 8px |
| Fuentes | las actuales: Fraunces (marca), Source Sans 3 (UI), JetBrains Mono | No hace falta cambiar familia |

**Opción de marca GallaIA** (a confirmar por Ociel): grafito `#202124`, burdeos `#7A1F2B`, crema `#F5F0E8`. Encaje: `--bg-elevated` grafito, `--orq` y primario burdeos, crema para texto principal o para el tema claro. El resto de estados (Running/Waiting/etc.) se mantienen de la tabla para no perder contraste.

Contraste mínimo texto/fondo: WCAG AA (4.5:1 en cuerpo, 3:1 en texto grande y en bordes de foco).

---

## 9. Responsive y accesibilidad

- **≥1280px:** layout de §3.
- **768–1279px:** el panel derecho pasa debajo del árbol (o se abre como cajón al seleccionar un agente). Sidebar en columna colapsable.
- **<768px:** una columna; nav inferior o menú; el árbol se apila (Orquestador, luego FE, luego BE); Quick Actions debajo del grafo; Chat a pantalla completa al entrar en un agente.

Accesibilidad (no negociable en cada fase):

- Navegación por teclado en nav, tarjetas, pestañas y cajas de prompt; foco visible (`:focus-visible`).
- El grafo y las líneas del árbol no son la única forma de leer las relaciones: la misma info va en texto/lista (como el panel de delegaciones de hoy).
- Badges con texto («En curso», «Espera aprobación»), no solo color.
- `prefers-reduced-motion`: sin animar el stream ni las líneas.
- Pedir el token con un formulario en Ajustes o un diálogo accesible; evitar el `window.prompt` actual en cuanto exista esa pantalla.
- Idioma de la UI: español, como ahora.

---

## 10. Plan de entrega (PRs pequeños)

Cada fase es un PR sobre rama `feat/...`, nunca sobre `master`. Criterio transversal: `npm run build` del frontend en verde. Sin secretos en logs ni en la UI.

### Fase A — MVP: cascarón + árbol + chat (recomendado como primer corte)

- Tokens oscuros y shell de 4 regiones.
- Árbol fijo Orquestador → FE, BE, con nombre, rol y prompt operativo en el raíz.
- Panel derecho, tab Chat, reutilizando la lógica de `ThreadsPage` (crear hilo, enviar, SSE, auto-avance, cerrar).
- Nav a las vistas ya existentes. Worktrees / Files / Tests / rama / Create Agent / Create Sub-agent: visibles pero deshabilitados.
- **Aceptación:** con el backend en local y token válido, se ven los 3 agentes; se crea un hilo; un mensaje al Orquestador aparece en el Chat y, con auto-avance, llegan respuestas por SSE sin recargar; un elemento sin API no finge datos.

### Fase B — Aprobaciones F2.2c en la UI

- Cliente contra `GET /api/v1/inbox` y `POST /inbox/{id}/decide`.
- Badge Waiting, aviso en la tarjeta y botones Aprobar/Rechazar (con nota opcional).
- Inbox del nav: primero las `thread_approval` abiertas; los handoffs AgentOS, aparte.
- **Aceptación:** con `GALLAIA_THREAD_APPROVAL=true`, una delegación deja el especialista en Waiting y el grafo en pausa; aprobar reanuda y aparece el resultado; rechazar deja el resultado de rechazo; con el flag apagado no se muestran acciones de decidir.

### Fase C — Grafo, proyecto y contadores

- Panel «Dependencies & Flow» con `GET /threads/{id}/delegations` y `pending_approval` de `graph-state`.
- Cabecera y pie: nombre del proyecto (`GET /projects`) y badge Activo/En reposo.
- Contadores Running / Waiting / Blocked / Completed derivados (§5). Paused = 0 o oculto.
- **Aceptación:** al terminar un avance, el grafo muestra pending/answered y, si hay resumen, lo indica; los números coinciden con hilos/inbox/sesiones reales; sin proyecto, no se inventa un nombre (se muestra el seed `default` o «Sin proyecto»).

### Fase D — Tabs con datos reales + pulido

- Context, Settings de solo lectura, ACL de FS como «permisos», Quick Actions definitivas, pestañas inferiores, uso LLM opcional en Ajustes, formulario del token, responsive y AA de §9.
- **Aceptación:** cada tab con API pinta datos reales; las tabs sin API siguen siendo placeholder; el token no se relee en claro después de guardarlo; ninguna llamada a endpoints de secretos en la UI; usable a teclado en las tres roturas de §9.

### Fase E — Posterior (no empezar ahora)

Worktrees y ramas, explorador de ficheros, tests, búsqueda en servidor, % de progreso de primera clase, alta de agentes, pausa global. Requieren backend nuevo y otra especificación.

---

## 11. Preguntas para Ociel

Las tres preguntas abiertas están en la cabecera de este documento (paleta, destino del prompt en las tarjetas FE/BE, y prioridad de la Inbox para las aprobaciones F2.2c). Esta propuesta no se implementa hasta que estén resueltas.

