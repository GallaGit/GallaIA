# Roadmap — GallaIA v2

Fuente de verdad del calendario **v2** (fases F0–F5). El roadmap AgentOS fases 0–7 está en [archive/ROADMAP-agentos-fases-0-7.md](archive/ROADMAP-agentos-fases-0-7.md).

**Estado (11-10-2026):** F0 hecho y fusionado. F1.1 (hilos y mensajes, backend) hecho. Siguiente: F1 (vista de conversación, UI + stream).

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
