# agentos.yml — Phase 6 (YAML / CLI)

Minimal YAML projection of the control plane: **agents** + **templates**.
Skills/grants/network/secrets in YAML and goal/task/skill CLI remain optional follow-ups; core push/pull + create/update is done.

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

- `app.services.agentos_yml`: `export_agentos_yml`, `import_agentos_yml`, `create_agent`, `update_agent`, `create_template`, `parse_agentos_yml`, `dump_agentos_yml`
- Target project: `--project-slug` / `project_slug=` (default `default`)

## CLI

From `backend/`:

```bash
python -m app.cli export -o agentos.yml   # alias: pull
python -m app.cli export --stdout
python -m app.cli import -i agentos.yml   # alias: push
python -m app.cli create-agent --name demo --role "Role prompt text"
python -m app.cli create-agent --from-yaml agent-snippet.yml
python -m app.cli update-agent --name demo --title "New title" --role "Updated role"
python -m app.cli create-template --slug lean-tmpl --name "Lean"  # optional; import preferred for steps
```

`export`/`pull` writes current agents+templates. `import`/`push` creates or updates by agent `name` / template `slug` (idempotent).
`create-agent` / `update-agent` write the same Agent rows that `GET /api/v1/agents` and YAML export show (UI list parity).

## Done when (Phase 6 core)

- Schema documented here
- Export → YAML; import → same agents+template in DB
- CLI create/update produces the same agents as import / UI list
- Pytest round-trip + CLI subprocess smoke
