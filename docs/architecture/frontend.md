# Frontend Architecture

## Purpose

Frame how the React + Vite atelier UI talks to the FastAPI control plane, and why UI concerns stay out of the FastAPI layer.

## Status

Draft

## Scope

- Existing: `frontend/` — React + Vite + TypeScript + Lucide; atelier theme; routes Agents, Tasks, Sessions, Inbox; Files/Settings placeholders; `src/api/client.ts` calling control-plane APIs (see [MODULE_BOUNDARIES.md](../product/MODULE_BOUNDARIES.md)).
- Planned: EmptyStates / shell for doc-only nav items only when explicitly scheduled; Isolation-era Files browser; no Phase 2+ product features in the Phase 1 MVP.
- Future: Auth UX (single operator), PWA inbox, live session viewer, Activity feed — [CONTROL_PLANE_NAV.md](../product/CONTROL_PLANE_NAV.md), [ROADMAP.md](../ROADMAP.md).

**Not** Next.js. **Not** a Temporada-1 chat UI as the current product surface.

## TODO

- Keep API base URL conventions (`VITE_API_URL`, Docker static proxy) documented in [frontend/README.md](../../frontend/README.md).
- Link screens to [design/atelier/screens.md](../design/atelier/screens.md).
- Do not add nav routes for Phase 2+ until the matching phase is in scope.
