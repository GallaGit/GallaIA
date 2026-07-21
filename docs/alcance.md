# Alcance del Proyecto

## Resumen

**GallaAI** es la marca y el nombre del producto. Es una plataforma de Inteligencia Artificial de largo plazo, orientada a aprendizaje profesional. El alcance del producto completo es modular y evolutivo; el alcance de cada temporada se limita a lo necesario para completar esa fase antes de avanzar.

Este documento define **qué entra**, **qué no entra** y **cómo se acota** el trabajo, con énfasis en la fase actual.

---

## Alcance del producto (visión a largo plazo)

La plataforma pretende evolucionar hacia un producto comparable, a nivel conceptual, a soluciones como ChatGPT, Claude Projects o Notion AI. No se busca copiarlas, sino aprender su arquitectura y buenas prácticas.

### Dentro del alcance futuro (por roadmap)

| Temporada | Enfoque |
|-----------|---------|
| 1 | Chat con IA |
| 2 | Persistencia e historial |
| 3 | RAG y documentos |
| 4 | Agentes inteligentes |
| 5 | Automatizaciones |
| 6 | Dashboard y administración |

Capacidades previstas a lo largo del ciclo de vida (solo cuando el roadmap lo indique):

- Chat con IA y API REST
- Usuarios, historial y base de datos
- Memoria, RAG y embeddings
- Agentes, tool calling y MCP
- Automatizaciones, dashboard e integraciones externas

### Fuera del alcance general del proyecto

- Proyectos desechables o demos aisladas que no se integren a la aplicación única
- Complejidad innecesaria o funcionalidades “por adelantado”
- Replicar de forma completa cualquier producto comercial existente
- Definir una visión de producto comercial cerrada en esta etapa (sigue en evolución; ver `docs/product-vision/`)

---

## Alcance de la fase actual: Temporada 1

**Objetivo:** chat con IA completamente funcional.

**Versión de referencia:** v0.1.0 (en planificación).

### Incluido

- Configuración del repositorio y del entorno de desarrollo
- Backend con **FastAPI** (Python)
- Frontend con **Next.js** + **React** + **TypeScript**
- Conexión con **un** proveedor de IA (OpenAI, Anthropic o Groq)
- Envío y recepción de mensajes
- Interfaz básica de chat
- Flujo: Usuario → Frontend → Backend → Proveedor de IA → Respuesta al usuario

### Excluido (hasta completar Temporada 1)

- Autenticación y gestión de usuarios
- Base de datos y persistencia del historial
- RAG, embeddings y carga de documentos
- Agentes, tool calling y MCP
- Automatizaciones
- Dashboard / administración
- Integraciones externas no necesarias para el chat básico
- Multi-proveedor simultáneo o selección avanzada de modelos
- Streaming avanzado, memoria a largo plazo u otras mejoras no imprescindibles para el criterio de éxito

### Criterio de éxito (definición de “hecho”)

La Temporada 1 se considera completada cuando el usuario pueda:

1. Abrir la aplicación
2. Escribir un mensaje
3. Enviarlo al modelo de IA
4. Recibir la respuesta en tiempo real

No se añadirá ninguna otra funcionalidad antes de alcanzar este objetivo.

---

## Stack dentro de alcance (base técnica)

| Capa | Tecnología |
|------|------------|
| Backend | Python, FastAPI |
| Frontend | React, Next.js, TypeScript |
| Base de datos | PostgreSQL *(a partir de Temporada 2)* |
| IA | OpenAI / Anthropic / Groq |
| DevOps | Docker, Docker Compose |

La base de datos forma parte del stack del proyecto, pero **no** del alcance implementable de la Temporada 1.

---

## Límites de proceso

- Una funcionalidad a la vez
- Cada entrega debe quedar integrada, documentada y funcional antes de la siguiente
- Documentar decisiones importantes
- Priorizar comprensión del problema y del diseño antes que velocidad

---

## Relación con otros documentos

| Documento | Rol |
|-----------|-----|
| `README.md` | Visión general, stack y roadmap |
| `docs/context.md` | Propósito, filosofía, principios y fase actual |
| `docs/product-vision/` | Visión de producto (en evolución) |
| `docs/alcance.md` | Este documento: límites de qué se construye y cuándo |

---

## Notas de mantenimiento

Cuando se cierre una temporada o se amplíe el alcance, actualizar este archivo para:

1. Marcar la temporada activa
2. Ajustar incluidos / excluidos
3. Redefinir el criterio de éxito de la nueva fase
