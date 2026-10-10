# Documentación GallaIA v2

Punto de entrada de la documentación del producto **v2** (equipo Orquestador / FE / BE).

## Canónicos v2

| Documento | Descripción |
|-----------|-------------|
| [VISION.md](VISION.md) | Visión del producto y los 3 agentes |
| [ARQUITECTURA.md](ARQUITECTURA.md) | 6 capas + tecnologías (mantener / añadir) |
| [ROADMAP.md](ROADMAP.md) | Fases F0–F5 (F0 hecho en el PR de reset) |

## Producto y control plane

| Documento | Descripción |
|-----------|-------------|
| [product/CONTROL_PLANE_NAV.md](product/CONTROL_PLANE_NAV.md) | Sidebar: implementado vs doc-only |
| [product/MODULE_BOUNDARIES.md](product/MODULE_BOUNDARIES.md) | Dos superficies API + ownership |
| [glossary.md](glossary.md) | Glosario |
| [context.md](context.md) | Contexto del repo |

## Arquitectura detallada (legado útil)

| Documento | Focus |
|-----------|-------|
| [architecture/overview.md](architecture/overview.md) | Overview |
| [architecture/backend.md](architecture/backend.md) | Backend |
| [architecture/frontend.md](architecture/frontend.md) | Frontend |
| [architecture/api.md](architecture/api.md) | HTTP API |
| [architecture/database.md](architecture/database.md) | SQLite actual; Postgres previsto |

## Backend / API / design / deploy

- Backend how-tos: [backend/](backend/)
- API: [api/](api/)
- ADR: [adr/](adr/)
- Design Atelier: [design/atelier/](design/atelier/)
- Deployment: [deployment/](deployment/)

## Archivo v1

Planes AgentOS (fases 0–7), PHASE1_GAPS, Lead Intake y docs de agentes retirados: **[archive/](archive/)** — solo historial.

## Smoke de links

```bash
python scripts/check-md-links.py
```
