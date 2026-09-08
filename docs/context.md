# Contexto del Proyecto

## Nombre / marca

**GallaAI** es el nombre oficial del proyecto y de la marca. No se usa otro nombre comercial (por ejemplo, “AI Workspace”).

---

## Propósito

Este proyecto nace con un doble objetivo:

1. Aprender de forma práctica las tecnologías utilizadas por un AI Engineer.
2. Construir una plataforma real que pueda evolucionar durante meses o años.

El proyecto NO pretende ser un ejercicio aislado.

Cada módulo deberá integrarse con los anteriores hasta formar una única aplicación. Hoy esa aplicación es el **control plane AgentOS** (agentes, Kanban, sesiones, inbox).

---

## Filosofía

Este proyecto prioriza el aprendizaje profundo sobre la velocidad de desarrollo.

Antes de implementar cualquier funcionalidad se debe comprender:

- qué problema resuelve;
- cómo funciona internamente;
- por qué se diseña de esa forma;
- cuáles son las alternativas;
- cuáles son sus ventajas y desventajas.

---

## Principios

- No construir proyectos desechables.
- No añadir complejidad innecesaria.
- Implementar una funcionalidad a la vez.
- Mantener el código limpio y modular.
- Documentar las decisiones importantes.
- Priorizar la comprensión antes que la velocidad.
- Phase 2+ se documenta antes de implementarse ([PHASE2_PLUS.md](agentos/PHASE2_PLUS.md)).

---

## Objetivo Final

Desarrollar una plataforma de IA modular. El camino **actual** es AgentOS (plano de control). Capacidades que pueden llegar más adelante, solo cuando el [ROADMAP](ROADMAP.md) lo indique:

- Agents, Tasks (Kanban), Sessions, Inbox
- Isolation / ACL, Templates, Goals, Triggers
- YAML / CLI, PWA, Activity feed
- Persistencia (SQLite hoy; Postgres cuando haga falta)
- Memoria, RAG, embeddings
- Chat de producto / API REST más rica
- Automatizaciones e integraciones externas

Estas funcionalidades no se desarrollarán todas desde el inicio.

---

## Fase Actual

## AgentOS Phase 1 (MVP)

### Objetivo

Operar un control plane AgentOS: ver agentes, crear tareas, lanzar runs (mock/stub), inspeccionar sesiones e inbox.

### Alcance

Esta fase incluye:

- configuración del proyecto y Docker;
- backend con FastAPI (`/api/v1`, `/api/v1/agentos`);
- frontend con React + Vite + Lucide (atelier);
- SQLite para el control plane;
- seeds, Kanban, sessions, inbox;
- runner mock y stub Anthropic Messages opcional.

No se implementan Isolation real, Goals, Templates, Triggers ni RAG hasta las fases documentadas en el roadmap.

Calendario: [ROADMAP.md](ROADMAP.md). Producto: [product/AGENTOS.md](product/AGENTOS.md). Alcance: [alcance.md](alcance.md).

---

## Arquitectura Inicial

```text
Operador (navegador)

↓

Frontend (React + Vite + atelier)

↓

Backend (FastAPI)

↓

SQLite + runner mock / stub Anthropic

↓

Kanban / Session / Inbox
```

Plataformas: Windows / Linux / macOS vía navegador + API. **No** Electron, Tauri ni exclusividad Mac.

---

## Metodología

El desarrollo seguirá un proceso incremental.

Cada nueva funcionalidad deberá:

1. resolver un problema concreto;
2. integrarse con la arquitectura existente;
3. ser documentada;
4. quedar completamente funcional antes de continuar.

---

## Definición de Éxito de la Phase 1

La Phase 1 se considera completada cuando el operador pueda:

- abrir la aplicación;
- crear o seleccionar una task;
- lanzar **Ejecutar ahora**;
- ver el avance del Kanban y el log de tool-calls en la session;
- usar el Inbox para atención humana cuando aplique.

Detalle y non-goals: [alcance.md](alcance.md), [product/AGENTOS.md](product/AGENTOS.md).
