# AgentOS API contract (canonical for feat/agentos-mvp)

Base: **`/api/v1/agentos`**
Branch: `feat/agentos-mvp` from `master` (push blocked until GitHub `contents:write`).

Shared staging on the box: `/workspace/gallaia-agentos/`

## Endpoints

| Method | Path | Body / notes |
|--------|------|----------------|
| GET | `/agents` | Seed catalog: `default`, `plan`, `senior-dev` |
| GET | `/agents/{name}` | One seed (prompts included) |
| POST | `/tasks` | `{ "name", "description"?, "assignee_agent"? }` → status `todo` |
| GET | `/tasks` | |
| GET | `/tasks/{id}` | |
| POST | `/tasks/{id}/run` | `{ "agent_name"?, "runner"?: "mock"\|"anthropic" }` |
| GET | `/sessions/{id}` | Includes `tool_events[]` |


| PATCH | `/tasks/{id}` | `{ "assignee_agent"?, "status"? }` kanban status |
| GET | `/inbox` | sessions `waiting-inbox` + tasks in `review` |

## Front wiring (Run now)

`POST /api/v1/agentos/tasks/{id}/run` with optional `{ "agent_name", "runner" }`.
Do **not** create a session first — the run endpoint creates the session and returns it.

## Kanban (mock runner)

`todo → doing → review → done` (MVP auto-closes review→done; approval gates later).

## Run response

```json
{
  "runner": "mock",
  "used_anthropic": false,
  "summary": "string",
  "task": { "id", "name", "description", "assignee_agent", "status", "activity", "created_at", "updated_at" },
  "session": {
    "id", "task_id", "agent_name", "runner", "status", "summary",
    "tool_events": [{ "name", "input", "output", "at" }],
    "started_at", "ended_at"
  }
}
```

## Env

```env
ANTHROPIC_API_KEY=     # optional; never hardcode / never commit
ANTHROPIC_MODEL=claude-sonnet-4-5
```

Without key (or `runner=mock`) → mock path only.

## Prompts

Every seed `foundational_prompt` / `role_prompt` labeled:

> Reconstructed from Danny Postma's AgentOS talk — not his verbatim prompt.

## Implementation files (ready to push)

- `backend/app/agentos/{__init__,seeds,models,store,runner,schemas}.py`
- `backend/app/api/routes/agentos.py`
- `backend/app/api/router.py` (includes agentos)
- `backend/app/core/config.py` (+ anthropic settings)
- `backend/.env.example`
- `backend/tests/test_agentos_runner.py`
- `docs/agentos/{README,PHASE2_PLUS}.md`

Phase 2+ (isolation, goals, triggers) = doc only in `docs/agentos/PHASE2_PLUS.md`.
