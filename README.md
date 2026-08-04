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

**Versión actual:** v0.1.0 (En planificación)

Estado:

- [x] Planificación inicial
- [x] Estructura de carpetas y documentación base (scaffold)
- [ ] Configuración del proyecto (dependencias, entorno)
- [ ] Backend runnable (FastAPI)
- [ ] Frontend
- [ ] Integración con LLM
- [ ] Chat funcional

---

## Stack tecnológico

Stack **elegido** (Planned). Aún no hay aplicación backend ejecutable ni dependencias instaladas en el repositorio.

### Backend (Planned)

- Python
- FastAPI
- SQLAlchemy (desde Temporada 2)
- PostgreSQL (desde Temporada 2)

### Frontend (Planned)

- React
- Next.js
- TypeScript

### IA (Planned)

- OpenAI, Anthropic o Groq (un proveedor en Temporada 1)

### DevOps (Planned)

- Docker
- Docker Compose (`backend/docker-compose.yml` — archivo vacío, pendiente de contenido)

---

## Roadmap

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
backend/          # Scaffold FastAPI (sin implementación aún)
frontend/         # Frontend (pendiente)
docs/             # Documentación
README.md
```

Compose y Docker del backend viven bajo `backend/` (`Dockerfile`, `docker-compose.yml`), hoy como archivos vacíos.

---

## Documentación

Índice completo: **[docs/README.md](docs/README.md)**.

Documentación de producto: `docs/alcance.md`, `docs/context.md`, `docs/product-vision/`.

---

## Licencia

MIT
