# Contexto del Proyecto

## Nombre

GallaAI

---

## Propósito

Este proyecto nace con un doble objetivo:

1. Aprender de forma práctica las tecnologías utilizadas por un AI Engineer.
2. Construir una plataforma real que pueda evolucionar durante meses o años.

El proyecto NO pretende ser un ejercicio aislado.

Cada módulo deberá integrarse con los anteriores hasta formar una única aplicación.

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

---

## Objetivo Final

Desarrollar una plataforma de IA modular que permita incorporar progresivamente funcionalidades como:

- Chat con IA
- API REST
- Usuarios
- Historial
- Base de datos
- Memoria
- RAG
- Embeddings
- Agentes
- Tool Calling
- MCP
- Automatizaciones
- Dashboard
- Integraciones externas

Estas funcionalidades no se desarrollarán desde el inicio.

Cada una se implementará únicamente cuando corresponda dentro del roadmap.

---

## Fase Actual

## Temporada 1

### Objetivo

Construir un Chat con IA completamente funcional.

### Alcance

Esta fase únicamente incluye:

- configuración del proyecto;
- backend con FastAPI;
- frontend con Next.js;
- conexión con un proveedor de IA;
- envío y recepción de mensajes;
- interfaz básica de chat.

No se implementarán funcionalidades adicionales hasta completar esta fase.

---

## Arquitectura Inicial

```text
Usuario

↓

Frontend (Next.js)

↓

Backend (FastAPI)

↓

Proveedor de IA

↓

Respuesta al usuario
```

---

## Metodología

El desarrollo seguirá un proceso incremental.

Cada nueva funcionalidad deberá:

1. resolver un problema concreto;
2. integrarse con la arquitectura existente;
3. ser documentada;
4. quedar completamente funcional antes de continuar.

---

## Definición de Éxito de la Fase 1

La primera fase se considerará completada cuando el usuario pueda:

- abrir la aplicación;
- escribir un mensaje;
- enviarlo al modelo de IA;
- recibir la respuesta en tiempo real.

No se añadirá ninguna otra funcionalidad antes de alcanzar este objetivo.
