# ADR-002: Layered Project Structure under `app/`

## Status

Accepted

## Context

The backend must grow from a minimal FastAPI app into chat, persistence, and later AI features without constant folder reshuffles. Educational clarity matters more than enterprise patterns (hexagonal, CQRS, DDD, feature-based packages).

## Decision

Keep a **layered** layout under `backend/app/` (`api`, `core`, `db`, `models`, `schemas`, `repositories`, `services`, plus reserved AI packages). Document the tree in `docs/ROADMAP.md` and treat docs structure as frozen; backend package layout changes require a new ADR with a strong technical reason.

## Consequences

- Clear ownership: routes vs config vs (future) services/repositories.
- Reserved folders (`agents/`, `rag/`, …) may exist before they have code; docs must label them Future/scaffold.
- Avoids premature abstraction while still preparing for Fase 3+.

## References

- [docs/backend/project-structure.md](../backend/project-structure.md)
- [docs/architecture/backend.md](../architecture/backend.md)
- [docs/ROADMAP.md](../ROADMAP.md)
