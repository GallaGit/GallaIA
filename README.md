# GallaAI

> Plataforma de IA desarrollada como proyecto de aprendizaje con enfoque profesional.

## Descripción

GallaAI es un proyecto de largo plazo cuyo objetivo es construir una plataforma moderna de Inteligencia Artificial similar, a nivel conceptual, a soluciones como ChatGPT, Claude Projects o Notion AI.

El propósito principal no es copiar estas herramientas, sino aprender las tecnologías, patrones de arquitectura y buenas prácticas utilizadas para desarrollar productos de IA reales.

Este proyecto crecerá por módulos, donde cada nueva funcionalidad se integrará sobre la anterior sin crear proyectos desechables.

---

## Objetivos

- Aprender desarrollo de aplicaciones con IA.
- Construir una arquitectura escalable y mantenible.
- Aplicar buenas prácticas de ingeniería de software.
- Crear un portafolio profesional basado en un producto real.

---

## Estado del proyecto

**Versión actual:** v0.1.0

- **Fase 1 — Foundation:** completada (FastAPI, Settings, logging, `/health`, Docker).
- **Fase 2 — API Base:** completada (router `/api/v1`, errores globales, middleware request-id, dependencias comunes).
- **Siguiente:** Fase 3 — Base de datos (PostgreSQL).

Checklist:

- [x] Planificación inicial
- [x] Estructura de carpetas y documentación base
- [x] Configuración del proyecto (dependencias, entorno)
- [x] Backend runnable (FastAPI + Docker)
- [ ] Frontend
- [ ] Integración con LLM
- [ ] Chat funcional

Roadmap técnico detallado: [docs/ROADMAP.md](docs/ROADMAP.md).

---

## Stack tecnológico

### Backend (Existing)

- Python
- FastAPI
- Docker / Docker Compose

### Backend (Planned)

- SQLAlchemy (Fase 3+)
- PostgreSQL (Fase 3+)

### Frontend (Planned)

- React
- Next.js
- TypeScript

### IA (Planned)

- OpenAI, Anthropic o Groq (un proveedor cuando llegue el chat)

---

## Roadmap de producto

### Temporada 1

Construcción del Chat con IA.

### Temporada 2

Persistencia de datos e historial.

### Temporada 3

RAG y documentos.

### Temporada 4

Agentes inteligentes.

### Temporada 5

Automatizaciones.

### Temporada 6

Dashboard y administración.

---

## Estructura del repositorio

```
backend/          # API FastAPI (Fase 1 + inicio Fase 2)
frontend/         # Frontend (pendiente)
docs/             # Documentación
README.md
```

Cómo arrancar el backend: **[backend/README.md](backend/README.md)**.

Docker vive bajo `backend/` (`Dockerfile`, `docker-compose.yml`).

---

## Documentación

Índice: **[docs/README.md](docs/README.md)**.

Producto: `docs/alcance.md`, `docs/context.md`, `docs/product-vision/`.

---

## Licencia

MIT
