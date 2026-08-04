# Architecture Overview

## Purpose

Provide a single map of GallaAI’s system shape: how frontend, backend, data, and AI providers relate over time, and why the project stays on a simple layered architecture.

## Status

Draft

## Scope

- Existing: Repository layout (`backend/`, `frontend/`, `docs/`); empty backend scaffold under `backend/app/`.
- Planned: Temporada 1 path — User → Next.js → FastAPI → one AI provider → response (see `docs/alcance.md` and `docs/context.md`).
- Future: Persistence, RAG, agents, automations, and dashboard in later seasons.

## Architectural stance

- Layered architecture under `backend/app/`.
- Not hexagonal, not CQRS, not DDD, not feature-based packages.
- Educational clarity over premature abstraction.

## TODO

- Add a high-level diagram (components and season when each appears).
- Link subsystem docs: [backend](backend.md), [frontend](frontend.md), [api](api.md), [database](database.md).
- Keep Existing vs Planned vs Future explicit in every update.
