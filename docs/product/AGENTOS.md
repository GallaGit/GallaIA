# GallaIA AgentOS — product map (Phase 0 + 1)

Inspired by Danny Postma AgentOS talk. Web control plane (FastAPI + React).
Runs on Windows / Linux / macOS in a browser. No Electron/Tauri/OS exclusivity.

## Mental model

- Project: workspace
- Agent: role + foundational/role prompts
- Task: Kanban todo|doing|review|done
- Session: run record + tool-call log
- Inbox: human interrupt channel

## Phase 1 vs later

| Feature | Phase 1 | Later |
|---------|---------|-------|
| Agents + prompts | seeded default/plan/senior-dev | ACL, skills, MCPs |
| Kanban + run now | mock/Claude stub | schedule, templates, chains |
| Session tool log | persisted events | live SSE + Agent SDK |
| Inbox | list + reply stub | resume session, PWA push |
| Isolation / R2 | docs + Files placeholder | real ACL + R2 MCP |
| Goals / triggers / YAML CLI | out of scope | Phase 4-6 |

## Prompts

All prompts are RECONSTRUCTED from the talk — not verbatim files.
See backend/app/services/prompts.py

## Module boundaries

See MODULE_BOUNDARIES.md. Backend owns persistence + runner; frontend owns atelier UI.
