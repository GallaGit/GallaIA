# Visión — GallaIA v2

Equipo agéntico **personal** para crear software. Ociel habla con el sistema; los agentes se coordinan entre sí (estilo teammates) para planificar, implementar, revisar e integrar.

## Agentes (F0)

| Agente | Rol |
|--------|-----|
| **Orquestador** | Habla con Ociel, planifica, divide en tareas, asigna a FE/BE, revisa e integra |
| **FE** | React / TypeScript / UI |
| **BE** | FastAPI / API / datos |

«Registrar agente» permanece visible pero **deshabilitado** («Próximamente») hasta F5.

## Qué no es v2 (aún)

- No runtime LangGraph / LiteLLM / MCP real (F2+)
- No registro libre de agentes ni protocolo A2A (F5)
- No RAG del repo ni Langfuse (F4)

La plataforma existente (tareas, sesiones, inbox, activity, triggers, grants, etc.) se mantiene como control plane mientras llega el runtime real.
