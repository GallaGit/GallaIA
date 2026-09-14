# Skills de código (skills.sh) — no el catálogo AgentOS

Esto cubre **skills de Cursor / agentes de código** instaladas con [skills.sh](https://skills.sh) (`npx skills add`).  
**No** es el catálogo de producto AgentOS `/skills` (eso es Fase 3 — [CONTROL_PLANE_NAV.md](../product/CONTROL_PLANE_NAV.md)).

## Por qué no están en git

El PR #12 (`feature/agent-skills`) intentó commitear un árbol `.agents/skills` + `skills-lock.json`: **~357 files / +200k líneas** (skills enteras + lock trees / junk). Eso no es mergeable.

Política:

- Instalar **en local** (o en el workspace del agente).
- **No** vendor lockfiles, `node_modules`, binarios ni copias completas de paquetes.
- `.agents/skills/` y `skills-lock.json` están en `.gitignore`.

## Instalación (máquina de desarrollo)

Desde la raíz del repo:

```bash
npx skills add find-skills
npx skills add vercel-react-best-practices
npx skills add web-design-guidelines
```

Review / verificación (Superpowers de obra, o equivalentes de mattpocock si el nombre del paquete cambia):

```bash
npx skills add obra/superpowers
```

Tras instalar, usa las skills `code-review` y `verification-before-completion` (nombres en Superpowers; no copiar el árbol al repo).

`find-skills` sirve para descubrir más paquetes sin ampliar el set por defecto.

## Set curado (este repo)

| Paquete | Para qué |
| ------- | -------- |
| `find-skills` | Descubrir skills.sh sin ampliar el vendor |
| `vercel-react-best-practices` | UI React/Vite (atelier) |
| `web-design-guidelines` | Layout / UI, no clonar Linear de Leads_CRM |
| `obra/superpowers` → `code-review`, `verification-before-completion` | Review y “¿está hecho de verdad?” antes de abrir PR |

No instalar Archify ni packs de a11y/Playwright **enteros** en git. Si hacen falta, `npx skills add` en local.

## Si un slice necesita una skill nueva

1. Añadir **una línea** a la tabla de arriba (nombre del paquete + para qué).
2. Instalarla en local.
3. No abrir un PR cuyo diff sea el contenido de `.agents/skills`.
