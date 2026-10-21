# Roadmap — GallaIA v2

Fuente de verdad del calendario **v2** (fases F0–F5). El roadmap AgentOS fases 0–7 está en [archive/ROADMAP-agentos-fases-0-7.md](archive/ROADMAP-agentos-fases-0-7.md).

**Estado (21-10-2026):** F0 hecho y fusionado. F1.1 (hilos y mensajes, backend), F1.2 (agentes responden en hilos, backend), F1.3 (vista de conversación en la UI), F1.4 (stream en vivo SSE de mensajes) y F1.5 (grafo de delegaciones + auto-avance opcional) hechos: **F1 cerrado**. F2 en curso: **F2.1 cerrado** — F2.1a (gateway de modelos con cadena OpenRouter → Groq → mock) y F2.1b (runner de sesiones por el gateway, modelo por agente, registro de uso y backend `litellm` opcional) hechos. **F2.2 en curso**: F2.2a (motor LangGraph opcional para los hilos, con checkpoints en memoria) hecho; F2.2b (checkpoints persistentes en SQLite y `GET /threads/{id}/graph-state`) hecho. Siguiente: F2.2c (interrupción humana: aprobación en Inbox sobre el grafo).

---

## F0 — Reset *(Hecho — PR #35, 11-10-2026)*

**Hecho**

- Seeds/default agents = exactamente **Orquestador**, **FE**, **BE**
- Eliminados seeds y plantillas ligados a agentes retirados (support, plan, senior-dev, lead-*, etc.) donde hacía falta consistencia
- Botón «Registrar agente» visible, deshabilitado, tooltip/etiqueta «Próximamente»
- Docs alineadas: README, VISION, ARQUITECTURA, este ROADMAP; obsoletas en `docs/archive/`

**Por hacer (no F0)**

- Mensajería entre agentes (F1)
- Runtime LangGraph + LiteLLM + MCP (F2+)

---

## F1 — Mensajería entre agentes

### Slice F1.1 — Hilos y mensajes (backend)

**Hecho**

- Modelos `Thread` (título, proyecto opcional, autor, estado open/closed) y `Message` (emisor, receptor, kind text/delegation/result, cuerpo)
- Validación de emisores/receptores contra agentes existentes (`orquestador`, `fe`, `be`) o `user`
- Schemas Pydantic + rutas REST `/api/v1/threads`: crear, listar, detalle (con mensajes ordenados), publicar mensaje y cerrar
- Reglas de error: 422 actor desconocido / delegación no autorizada, 404 hilo inexistente, 409 publicar en hilo cerrado
- Evento de actividad `message.created` reutilizando el helper existente
- Tests en `backend/tests/test_threads.py`

**Por hacer**

- Vista de conversación en la UI (hecho en F1.3)
- Stream en vivo (SSE) de mensajes nuevos (hecho en F1.4)
- Delegación Orquestador → FE / BE visible en el grafo del orquestador (hecho en F1.5)


### Slice F1.2 — Agentes responden en hilos (backend)

**Hecho**

- Servicio `advance_thread(db, thread, max_steps=6, llm=None)`: responde mensajes dirigidos a un agente (`orquestador`/`fe`/`be`) que aún no tienen respuesta suya, de más antiguo a más nuevo, con tope de `max_steps` por llamada (evita bucles)
- Orquestador con `text` de `user`: plan corto + una o dos `delegation` a `fe`/`be`; decide vía LLM pidiendo solo JSON `{"plan", "delegations"}` con parseo defensivo y fallback a delegar el texto del usuario a ambos
- `fe`/`be` con `delegation`: una `result` de vuelta al orquestador usando `foundational_prompt` + `role_prompt` como system
- Orquestador con `result`: cuando todas sus delegaciones del hilo tienen resultado, publica un `text` de resumen a `user`; si no, no responde
- LLM inyectable; por defecto usa OpenRouter si hay clave y si no un mock determinista (rol-etiquetado y, para el plan, el fallback)
- Nunca responde a sí mismo ni a mensajes a `user`/broadcast; hilo cerrado → `ConflictError`
- Cada mensaje creado emite el evento de actividad `message.created`
- Ruta `POST /api/v1/threads/{id}/advance` (query `max_steps` 1..20, default 6) → `{"created": [MessageOut...]}`; 404 hilo inexistente, 409 cerrado
- Tests en `backend/tests/test_thread_agents.py` con LLM falso inyectado (sin red)

**Por hacer**

- Botón / auto-advance en la UI para disparar las respuestas (hecho en F1.3–F1.5)
- Resumen y delegaciones visibles en el grafo del orquestador (hecho en F1.5)
- Enrutado real por modelo en lugar del mock (hecho en F2.1a–F2.1b: gateway OpenRouter → Groq → mock, modelo por agente, `litellm` opcional)



### Slice F1.3 — Vista de conversación (UI) *(Hecho — 13-10-2026)*

**Hecho**

- Cliente API (`frontend/src/api/client.ts`): tipos `Thread`, `ThreadDetail`, `ThreadMessage` y llamadas a `/api/v1/threads` (listar, crear, detalle, publicar mensaje, avanzar, cerrar)
- Página `Conversaciones` (`/threads` y `/threads/:id`) en la navegación principal: lista de hilos, crear hilo, detalle con mensajes en orden (emisor → receptor, tipo `text`/`delegation`/`result` con etiqueta)
- Composer para escribir al Orquestador como `user`, botón «Avanzar» (desde F1.4 reabre el stream en vivo en lugar de `POST /advance` + recargar) y botón «Cerrar hilo»
- Estados de error: API caída, hilo cerrado (409) y vacío

**Por hacer**

- Stream en vivo (SSE) de mensajes nuevos en lugar de recargar tras «Avanzar» (hecho en F1.4)
- Auto-advance opcional al enviar (hecho en F1.5)
- Delegaciones visibles en el grafo del orquestador (hecho en F1.5)
- Tests de frontend (no hay runner de tests en el frontend todavía; hoy se valida con `npm run build`)

### Slice F1.4 — Stream en vivo SSE de mensajes *(Hecho — 15-10-2026)*

**Hecho**

- Backend `GET /api/v1/threads/{id}/stream` (`text/event-stream`): reenvía los mensajes existentes del hilo y luego ejecuta `advance_thread` paso a paso con el LLM mock determinista (sin necesidad de clave de API), emitiendo cada mensaje nuevo (plan, delegaciones, resultados, resumen) como evento `message` en cuanto se guarda; cierra con `end: {reason: done, created}`. Mismo contrato de errores que `POST /advance`: 404 hilo inexistente, 409 hilo cerrado. Query `max_steps` (1..20, default 6), `heartbeat_seconds` y `max_seconds` opcional
- Servicio `backend/app/services/thread_stream.py` con sesiones DB cortas por paso (mismo patrón que `session_sse_stream`)
- Frontend (`frontend/src/pages/ThreadsPage.tsx` + `api.threadStreamUrl`): la vista Conversaciones abre un `EventSource` al hilo activo y añade los mensajes a la lista según llegan, sin recargar; «Avanzar» y «Enviar al Orquestador» reabren el stream en lugar de recargar el detalle; pill «en directo» mientras transmite; se cierra al cambiar de hilo o salir de la página
- Tests en `backend/tests/test_thread_stream.py`: eventos recibidos (plan/delegaciones/resultados/resumen + `end: done`), 409 en hilo cerrado, 404 en hilo inexistente

**Por hacer**

- Auto-advance opcional al enviar (hecho en F1.5)
- Delegaciones visibles en el grafo del orquestador (hecho en F1.5)

### Slice F1.5 — Grafo de delegaciones y auto-avance opcional *(Hecho — 15-10-2026)*

**Hecho**

- Backend `GET /api/v1/threads/{id}/delegations`: grafo del hilo con nodos (`user`, `orquestador`, `fe`, `be`) y una arista por cada `delegation` del Orquestador con su estado (`pending` / `answered`) y el id del `result` que la responde (mismo emparejamiento que el resumen de F1.2: primer `result` del destinatario posterior a la delegación); incluye el id del mensaje de resumen al usuario si existe. 404 hilo inexistente
- Tests en `backend/tests/test_thread_delegations.py`
- Frontend (`ThreadsPage.tsx`): panel «Delegaciones» con Orquestador → FE / BE, estado de cada delegación y si ya hay resumen; se refresca al terminar el stream
- Interruptor «Avanzar automáticamente al enviar» (guardado en `localStorage`, activado por defecto): si está apagado, enviar solo publica el mensaje y hay que pulsar «Avanzar»

**Por hacer**

- Runtime real con LiteLLM / LangGraph (F2)
- Tests de frontend (sigue sin runner; se valida con `npm run build`)

---

## F2 — Runtime real

### Slice F2.1a — Gateway de modelos: OpenRouter → Groq → mock *(Hecho — 17-10-2026)*

**Hecho**

- Módulo `backend/app/llm/gateway.py`: una sola entrada `complete(system, user)` para los agentos de los hilos, con cadena de proveedores en orden: **OpenRouter** (principal), **Groq** (respaldo) y **mock determinista** (sin clave o si todos fallan). Nombres de modelo estilo LiteLLM (`openrouter/<modelo>`, `groq/<modelo>`) para que el cambio a LiteLLM sea directo
- Groq vía su endpoint compatible con OpenAI (`https://api.groq.com/openai/v1`), configurable con `GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_BASE_URL` (en `.env.example`, sin claves reales)
- Si un proveedor falla (red/HTTP/respuesta vacía) se pasa al siguiente; el resultado indica qué proveedor y modelo respondió
- `default_llm()` de F1.2 usa el gateway (sin claves sigue siendo el mock, igual que antes)
- Tests en `backend/tests/test_llm_gateway.py` con transporte HTTP falso (sin red)

**Pasado a F2.1b** (ver abajo): runner de sesiones por el gateway, modelo por agente, registro de uso y backend `litellm` opcional.

### Slice F2.1b — Runner por el gateway, modelo por agente, uso y `litellm` opcional *(Hecho — 18-10-2026)*

**Hecho**

- Runner de sesiones del control plane (`services/runner.py`, `POST /tasks/{id}/run`) y runner AgentOS en memoria (`agentos/runner.py`) llaman al gateway en lugar de a OpenRouter directo: misma cadena OpenRouter → Groq → mock. `session.runner` guarda el proveedor que respondió (`openrouter` / `groq` / `mock`); un evento `<proveedor>.error` por cada proveedor que falla y `llm.fallback` si acaba en mock. Sin claves todo sigue igual (ruta mock con los eventos de grants/red/fs). Se quita la ruta Anthropic del runner del control plane (el runner en memoria la mantiene solo si se pide explícitamente y hay `ANTHROPIC_API_KEY`)
- Modelo por agente: `Agent.model` se respeta en el gateway (`resolve_model` / `providers_for_model`): id de OpenRouter (`vendor/modelo[:free]` u `openrouter/<id>`) sustituye el modelo de OpenRouter (Groq sigue de respaldo con su modelo); `groq/<id>` usa Groq primero con ese modelo; `mock` no llama a nadie; vacío/`inherit` y los valores heredados `claude-*` usan el modelo configurado (`OPENROUTER_MODEL`), así las filas antiguas siguen funcionando sin migrar datos. Los agentes de los hilos (F1.2) leen el modelo de la tabla `agents` (con el de la semilla como respaldo)
- Valores por defecto `claude-sonnet-4` (modelo `Agent`, `agentos.yml`, `create_agent`, CLI `create-agent --model`) cambiados a `DEFAULT_OPENROUTER_MODEL`
- Registro de uso: tabla `llm_usage` (creada por `create_all` en `init_db`, como el resto) con una fila por intento: origen (`thread` / `session`), agente, proveedor, modelo, backend, ok/error (recortado y sin claves), tokens de entrada/salida (si la respuesta trae `usage`), latencia en ms, coste (0 para modelos `:free` y mock; vacío en el resto), `session_id` / `thread_id`. Nunca guarda prompts ni respuestas. También se escribe una línea en el log `app.llm.usage`. Consulta: `GET /api/v1/llm/usage?limit=50` (últimas llamadas + totales por proveedor/modelo)
- Backend `litellm` opcional detrás del mismo gateway: `GALLAIA_LLM_BACKEND=litellm` (por defecto `http`). `litellm` no es dependencia (ni en `pyproject.toml` ni en los lockfiles): hay que instalarlo a mano; si falta, se avisa en el log y se usa `http`
- Tests sin red: `backend/tests/test_llm_f21b.py` (transporte y módulo `litellm` falsos) y `backend/tests/conftest.py`, que vacía `OPENROUTER_API_KEY` / `GROQ_API_KEY` / `ANTHROPIC_API_KEY` en cada test para que un `.env` local con claves reales nunca provoque llamadas de red

**Por hacer**

- Precios reales por modelo (no `:free`) y trazas → Langfuse en F4
- Vista del uso en la UI (hoy solo API)
- Añadir `litellm` como extra `[llm]` con hashes cuando entre LangGraph (F2.2) y los lockfiles con hashes estén en `master`

### Slice F2.2a — Motor LangGraph opcional para los hilos *(Hecho — 19-10-2026)*

**Hecho**

- Módulo `backend/app/runtime/thread_graph.py`: el avance de un hilo (Orquestador → FE / BE → resumen) como `StateGraph` de LangGraph con nodos `pick` (siguiente mensaje pendiente), `orquestador` y `specialist`, y bucle hasta que no quedan pendientes o se alcanza `max_steps`. Reutiliza los mismos handlers de F1.2, así que el resultado es idéntico al motor clásico
- Estado del grafo solo con datos primitivos (id del hilo, pasos, ids creados y gestionados); la sesión de BD y el LLM van por `config["configurable"]`, no en el estado
- Checkpoints en memoria (`MemorySaver`) con `thread_id = "thread-<id>"`: se puede consultar el último estado del grafo de cada hilo (`get_thread_graph_state`)
- Interruptor `GALLAIA_THREAD_ENGINE=langgraph` (por defecto `classic`). Si `langgraph` no está instalado, se avisa en el log y se usa el motor clásico. `advance_thread`, `POST /advance` y el stream SSE (que usa `advance_thread` paso a paso) mantienen el mismo contrato
- `langgraph` no es dependencia (ni en `pyproject.toml` ni en los lockfiles), igual que `litellm`: hay que instalarlo a mano (`pip install langgraph`)
- Tests en `backend/tests/test_thread_graph.py` (se saltan si falta `langgraph`): mismos mensajes que el motor clásico con LLM falso, tope de pasos, checkpoint consultable y vuelta al motor clásico si falta la librería

**Por hacer**

- ~~F2.2b: checkpoints persistentes~~ (hecho, ver abajo)
- Añadir `langgraph` (y `litellm`) como extra `[llm]` con hashes en los lockfiles y activarlo por defecto
- Interrupciones humanas (aprobación en Inbox) sobre el grafo, base para F3

### Slice F2.2b — Checkpoints persistentes en SQLite *(Hecho — 21-10-2026)*

**Hecho**

- Checkpointer persistente `SqliteSaver` (`langgraph-checkpoint-sqlite`, opcional como `langgraph`) en un fichero aparte, `GALLAIA_CHECKPOINT_DB` (por defecto `./data/checkpoints.db`, fuera de git). Con `memory` o sin la librería se usa `MemorySaver` como en F2.2a
- El estado del grafo de cada hilo sobrevive a un reinicio del backend; avanzar un hilo a medias tras reiniciar sigue desde los mensajes de la BD, sin repetir respuestas
- Endpoint de solo lectura `GET /api/v1/threads/{id}/graph-state` (motor, tipo de checkpointer y último estado; `null` si no hay)
- Tests sin red con fichero temporal: persistencia tras "reinicio" simulado, reanudación sin duplicados, `memory` y falta de la librería

**Por hacer**

- Postgres como checkpointer cuando migremos la BD (resto de F2)
- Limpieza/retención de checkpoints antiguos
- Interrupciones humanas (aprobación en Inbox) sobre el grafo, base para F3
- Extra `[llm]` con `langgraph`, `langgraph-checkpoint-sqlite` y `litellm` con hashes en los lockfiles

**Por hacer (resto de F2)**

- Migrar la base de datos de SQLite a Postgres (Docker en local o Supabase) usando el `DATABASE_URL` ya previsto en `.env`; requisito para checkpoints de LangGraph y para pgvector en F4. Hasta entonces se sigue con SQLite.
- Herramientas MCP en workspace git con sandbox Docker

---

## F3 — Ciclo de software

**Por hacer**

- Flujo idea → plan → código → tests → PR en GitHub
- Aprobación humana en Inbox

---

## F4 — Memoria

**Por hacer**

- RAG del repo (pgvector sobre el Postgres de F2)
- Langfuse (trazas / costes)

---

## F5 — Escalar

**Por hacer**

- Registrar agentes (habilitar el CTA)
- Protocolo A2A
- Push real
