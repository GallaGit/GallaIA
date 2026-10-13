# Roadmap — GallaIA v2

Fuente de verdad del calendario **v2** (fases F0–F5). El roadmap AgentOS fases 0–7 está en [archive/ROADMAP-agentos-fases-0-7.md](archive/ROADMAP-agentos-fases-0-7.md).

**Estado (13-10-2026):** F0 hecho y fusionado. F1.1 (hilos y mensajes, backend) y F1.2 (agentes responden en hilos, backend) hechos. F1.3 (vista de conversación en la UI) en curso. Siguiente: F1.4 (stream en vivo SSE de mensajes).

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

- Vista de conversación en la UI
- Stream en vivo (SSE) de mensajes nuevos
- Delegación Orquestador → FE / BE visible en el grafo del orquestador


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

- Botón / auto-advance en la UI para disparar las respuestas
- Resumen y delegaciones visibles en el grafo del orquestador
- Enrutado real por modelo (LiteLLM) en lugar del mock (F2+)



### Slice F1.3 — Vista de conversación (UI)

**Hecho**

- Cliente API (`frontend/src/api/client.ts`): tipos `Thread`, `ThreadDetail`, `ThreadMessage` y llamadas a `/api/v1/threads` (listar, crear, detalle, publicar mensaje, avanzar, cerrar)
- Página `Conversaciones` (`/threads` y `/threads/:id`) en la navegación principal: lista de hilos, crear hilo, detalle con mensajes en orden (emisor → receptor, tipo `text`/`delegation`/`result` con etiqueta)
- Composer para escribir al Orquestador como `user`, botón «Avanzar» (`POST /advance`) que añade las respuestas de los agentes y botón «Cerrar hilo»
- Estados de error: API caída, hilo cerrado (409) y vacío

**Por hacer**

- Stream en vivo (SSE) de mensajes nuevos en lugar de recargar tras «Avanzar» (F1.4)
- Auto-advance opcional al enviar
- Delegaciones visibles en el grafo del orquestador
- Tests de frontend (no hay runner de tests en el frontend todavía; hoy se valida con `npm run build`)

---

## F2 — Runtime real

**Por hacer**

- LangGraph (estado + checkpoints)
- LiteLLM (capa de modelos)
- Herramientas MCP en workspace git con sandbox Docker

---

## F3 — Ciclo de software

**Por hacer**

- Flujo idea → plan → código → tests → PR en GitHub
- Aprobación humana en Inbox

---

## F4 — Memoria

**Por hacer**

- RAG del repo (Postgres + pgvector)
- Langfuse (trazas / costes)

---

## F5 — Escalar

**Por hacer**

- Registrar agentes (habilitar el CTA)
- Protocolo A2A
- Push real
