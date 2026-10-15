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

**Mantener:** FastAPI, SQLAlchemy, Pydantic, React/Vite/TS, Docker, pytest, SSE, OpenRouter (proveedor principal).

**Añadir (F2+):** LangGraph (orquestación con estado y checkpoints), LiteLLM (capa de modelos: enrutado OpenRouter → Groq como fallback planificado), MCP (herramientas), Postgres+pgvector (RAG del código, F4), Langfuse (trazas/costes), Playwright (verificación FE).

**Futuro:** protocolo A2A para agentes externos.

## Estado actual (F0)

- Backend: FastAPI + SQLAlchemy/SQLite; seeds `orquestador`, `fe`, `be`
- Frontend: React/Vite atelier (Kanban, agentes, sesiones, inbox, activity, live)
- Runtime: mock por defecto; OpenRouter como proveedor principal (`backend/app/providers/openrouter.py`); Groq planificado como fallback (no implementado); stub Anthropic legacy, a eliminar (no grafo LangGraph)

> **Proveedores LLM:** OpenRouter es el proveedor principal (implementado en `backend/app/providers/openrouter.py`, modelo gratuito por defecto `nvidia/nemotron-3-ultra-550b-a55b:free`). Groq está planificado como fallback (aún no implementado; se prevé una variable `GROQ_API_KEY`). Anthropic es opcional/legacy: las variables `ANTHROPIC_*` y el stub Messages siguen en el código pero no son el proveedor previsto y se eliminarán/sustituirán en un PR de código posterior. El enrutado entre proveedores se hará con LiteLLM (F2+).
>
> Nota: los modelos gratuitos de OpenRouter tienen límites de uso bajos y pueden desaparecer sin aviso; configura siempre un modelo de fallback.

Detalle de módulos legacy del control plane: [product/MODULE_BOUNDARIES.md](product/MODULE_BOUNDARIES.md). Diagramas antiguos de AgentOS: [archive/](archive/).
