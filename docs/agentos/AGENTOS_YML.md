# agentos.yml — Phase 6 slice 1

Minimal YAML projection of the control plane: **agents** + **templates**.  
Full Admin sync (skills, grants, network, secrets, goals, CLI parity) is later.

Aligned with [POSTMA_WALKTHROUGH.md](POSTMA_WALKTHROUGH.md) §2.13 / Fase 6 and [ROADMAP.md](../ROADMAP.md).

## Schema (version 1)

```yaml
version: 1
agents:
  - name: yaml-demo          # idempotent key
    title: YAML Demo Agent
    model: claude-sonnet-4
    foundational_prompt: "..."
    role_prompt: "..."
    runner_preference: mock  # mock | cloud | local | …
templates:
  - slug: yaml-demo-template # idempotent key
    name: YAML Demo Template
    description: optional
    steps:
      - position: 1
        name: Step one
        description: optional
        assignee_agent_name: yaml-demo
        approval_gate: true
        requires_previous_done: false
```

| Field | Notes |
| ----- | ----- |
| `version` | Must be `1` for this slice |
| `agents[].name` | Unique within project; import upserts |
| `templates[].slug` | Globally unique in DB; import upserts steps (replace) |
| Isolation (grants/network/fs/secrets) | **Not** in v1 YAML — follow-up |
| Skills | **Not** in v1 YAML — follow-up |

## Module

- `app.services.agentos_yml`: `export_agentos_yml`, `import_agentos_yml`, `parse_agentos_yml`, `dump_agentos_yml`
- Target project: `--project-slug` / `project_slug=` (default `default`)

## CLI

From `backend/`:

```bash
python -m app.cli export -o agentos.yml
python -m app.cli export --stdout
python -m app.cli import -i agentos.yml
```

`export` writes current agents+templates. `import` creates or updates by agent `name` / template `slug` (idempotent).

## Done when (slice 1)

- Schema documented here
- Export → YAML; import → same agents+template in DB
- Pytest round-trip / import creates matching agent