# AgentOS MVP (GallaIA)

Backend slice for AgentOS Phase 1 on branch `feat/agentos-mvp` (from `master`).

## Scope (this PR)

- Agent **seeds**: `default`, `plan`, `senior-dev`
- Prompts **reconstructed** from Danny Postma's AgentOS talk — **not verbatim**
- **Session runner**: mock advances kanban `todo → doing → review → done` and appends a tool-event log
- **Optional LLM**: if `OPENROUTER_API_KEY` is set, call Chat Completions; else if `ANTHROPIC_API_KEY` is set and `runner=anthropic`, call Messages API; otherwise mock
- No Mac-only paths, no Cursor Cloud Agents in this slice

## API contract

Base: `/api/v1/agentos`

| Method | Path | Notes |
|--------|------|--------|
| GET | `/agents` | Seed catalog |
| GET | `/agents/{name}` | One seed |
| POST | `/tasks` | `{ name, description?, assignee_agent? }` → task `todo` |
| GET | `/tasks` | List in-memory tasks |
| GET | `/tasks/{id}` | |
| POST | `/tasks/{id}/run` | Optional body `{ agent_name?, runner?: "mock"\|"anthropic"\|"openrouter" }` |
| GET | `/sessions/{id}` | Includes `tool_events` |

Store is **process memory** (MVP). Persistence is Backend/Phase DB work.

## Env

```env
OPENROUTER_API_KEY=   # optional; never commit
OPENROUTER_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
ANTHROPIC_API_KEY=   # optional; never commit
ANTHROPIC_MODEL=claude-sonnet-4-5   # optional override
```

## Prompt labeling

Every seed file and prompt string starts with / documents:

> Reconstructed from Danny Postma's AgentOS talk — not his verbatim prompt.

## Out of scope here

Isolation ACLs, templates, goals/orchestrator, triggers/webhooks — see [PHASE2_PLUS.md](PHASE2_PLUS.md) and [ROADMAP.md](../ROADMAP.md) (sketch only). Sidebar map (doc only): [CONTROL_PLANE_NAV.md](../product/CONTROL_PLANE_NAV.md).

Walkthrough del video de Postma (qué construyó y en qué orden replicarlo): [POSTMA_WALKTHROUGH.md](POSTMA_WALKTHROUGH.md).
