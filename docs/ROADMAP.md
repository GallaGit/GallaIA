# Roadmap — GallaIA v2

Fuente de verdad del calendario **v2** (fases F0–F5). El roadmap AgentOS fases 0–7 está en [archive/ROADMAP-agentos-fases-0-7.md](archive/ROADMAP-agentos-fases-0-7.md).

---

## F0 — Reset *(Hecho en este PR)*

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

**Por hacer**

- Hilos y mensajes entre agentes
- Delegación Orquestador → FE / BE
- Vista de conversación en la UI

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
