# Arquitectura — GallaIA v2

Seis capas (propuesta 2026-10-11). Hoy el control plane cubre sobre todo 1–4 con SQLite y runners mock/LLM stub; las capas 5–6 se profundizan en F2+.

## Capas

| # | Capa | Contenido |
|---|------|-----------|
| 1 | **Interfaz** | React 19 + Vite (PWA), CLI |
| 2 | **API** | FastAPI REST + SSE/WebSocket |
| 3 | **Aplicación / orquestación** | Casos de uso + grafo del orquestador |
| 4 | **Dominio** | Proyecto, Agente, Tarea, Mensaje/Hilo, Sesión, Artefacto, Aprobación |
| 5 | **Runtime de agentes** | Bucle LLM + herramientas (fs, git, shell, tests) vía MCP, en sandbox |
| 6 | **Infraestructura** | Postgres (+pgvector), workspace git por proyecto en Docker, proveedor LLM abstraído, observabilidad |

## Tecnologías

**Mantener:** FastAPI, SQLAlchemy, Pydantic, React/Vite/TS, Docker, pytest, SSE, OpenRouter/Anthropic.

**Añadir (F2+):** LangGraph (orquestación con estado y checkpoints), LiteLLM (capa de modelos), MCP (herramientas), Postgres+pgvector (RAG del código, F4), Langfuse (trazas/costes), Playwright (verificación FE).

**Futuro:** protocolo A2A para agentes externos.

## Estado actual (F0)

- Backend: FastAPI + SQLAlchemy/SQLite; seeds `orquestador`, `fe`, `be`
- Frontend: React/Vite atelier (Kanban, agentes, sesiones, inbox, activity, live)
- Runtime: mock por defecto; OpenRouter/Anthropic opcionales (stubs, no grafo LangGraph)

Detalle de módulos legacy del control plane: [product/MODULE_BOUNDARIES.md](product/MODULE_BOUNDARIES.md). Diagramas antiguos de AgentOS: [archive/](archive/).
