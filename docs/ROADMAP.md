# Estructura de documentación congelada

```text
docs/
├── README.md
│
├── architecture/
│   ├── overview.md
│   ├── backend.md
│   ├── frontend.md
│   ├── database.md
│   └── api.md
│
├── backend/
│   ├── project-structure.md
│   ├── request-lifecycle.md
│   ├── configuration.md
│   ├── dependency-injection.md
│   ├── routing.md
│   ├── services.md
│   ├── repositories.md
│   ├── data-models.md
│   ├── error-handling.md
│   ├── logging.md
│   ├── testing.md
│   └── glossary.md
│
├── adr/
│   ├── README.md
│   ├── ADR-001-fastapi.md
│   ├── ADR-002-project-structure.md
│   └── ADR-003-postgresql.md
│
└── assets/
    └── diagrams/
```

Y también estoy de acuerdo con tu otra decisión: **no queremos una enciclopedia**, queremos documentación útil.

---

## ¿Qué responsabilidad tendrá cada documento?

Muy resumido:

| Documento | Responsabilidad |
| --------- | --------------- |
| `project-structure.md` | Explicar la estructura del proyecto y el propósito de cada carpeta. |
| `request-lifecycle.md` | Explicar el recorrido de una petición HTTP. |
| `configuration.md` | Explicar cómo se configura la aplicación (`.env`, `settings`, etc.). |
| `dependency-injection.md` | Explicar cómo funciona `Depends()` y dónde usarlo. |
| `routing.md` | Organización de routers y endpoints. |
| `services.md` | Reglas para la lógica de negocio. |
| `repositories.md` | Acceso a la base de datos. |
| `data-models.md` | Modelos SQLAlchemy y esquemas Pydantic. |
| `error-handling.md` | Gestión de errores y excepciones. |
| `logging.md` | Estrategia de logs. |
| `testing.md` | Organización de las pruebas. |

Cada documento debería tener entre **2 y 5 páginas**, no 20.

---

## ¿Qué viene después de la documentación?

Aquí es donde quiero ser muy estricto para mantener el proyecto "on track".

La documentación que estamos escribiendo **no es el objetivo**, es la preparación.

Después de terminar estos documentos, **no empezaría por hacer un chat con IA**.

Empezaría por construir la base del backend.

## Roadmap técnico

### Fase 1 — Foundation

- Estructura del proyecto ✅
- Documentación ✅
- Inicializar FastAPI ✅
- Configuración (`Settings`) ✅
- Logging ✅
- Health endpoint (`GET /health`) ✅
- Docker ✅
- Docker Compose ✅

### Fase 2 — API Base

- API Router ✅
- Versionado (`/api/v1`) ✅
- Manejo global de errores
- Middleware
- Dependencias comunes

### Fase 3 — Base de datos

- PostgreSQL
- SQLAlchemy
- Alembic
- Primera conexión
- Modelo `User`

### Fase 4 — Autenticación

- Registro
- Login
- JWT
- Hash de contraseñas

### Fase 5 — Usuarios

- CRUD de usuarios
- Perfil
- Roles

### Fase 6 — Chat
