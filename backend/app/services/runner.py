"""
Task runner: mock by default; optional Claude path if ANTHROPIC_API_KEY is set.

Phase 1 MVP: simulated session that updates DB and emits fake tool events.
Real Claude Agent SDK integration is optional and best-effort.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Agent, AgentSession, InboxMessage, Task


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _append_event(session: AgentSession, events: list, name: str, detail: str) -> None:
    events.append(
        {
            "ts": _now().isoformat(),
            "tool": name,
            "detail": detail,
        }
    )
    session.set_tool_events(events)


def run_task_session(db: Session, task: Task, agent: Agent) -> AgentSession:
    """Start a (mock or Claude) session for a task and update status."""
    use_claude = bool(os.getenv("ANTHROPIC_API_KEY"))
    runner_name = "claude" if use_claude else "mock"

    session = AgentSession(
        agent_id=agent.id,
        task_id=task.id,
        runner=runner_name,
        status="starting",
        tool_call_log="[]",
    )
    db.add(session)
    task.status = "doing"
    db.flush()

    events: list = []
    session.status = "running"
    _append_event(session, events, "session.start", f"Runner={runner_name} agent={agent.name}")
    _append_event(
        session,
        events,
        "prompt.load",
        "Loaded foundational + role prompts (RECONSTRUCTED — not verbatim)",
    )
    _append_event(session, events, "task.read", f"Task #{task.id}: {task.name}")

    if use_claude:
        # Optional real path: call Anthropic Messages API if available.
        # Still a stub relative to full Agent SDK (no tools/MCP/container).
        try:
            summary = _run_claude_stub(agent, task)
            _append_event(session, events, "claude.messages", "Completed Messages API call")
        except Exception as exc:  # noqa: BLE001 — MVP: fall back to mock
            summary = f"Claude call failed ({exc}); finished with mock summary."
            _append_event(session, events, "claude.error", str(exc))
    else:
        summary = (
            f"[mock] Agent '{agent.name}' completed task '{task.name}'. "
            "Set ANTHROPIC_API_KEY for optional Claude Messages stub."
        )
        _append_event(session, events, "mock.think", "Simulating tool use…")
        _append_event(session, events, "mock.write", "Would write via filesystem MCP")
        _append_event(session, events, "agentos.task_update", "Marking task complete")

    if task.approval_gate:
        task.status = "review"
        _append_event(session, events, "agentos.gate", "Approval gate → left in review")
        inbox = InboxMessage(
            from_role="agent",
            agent_id=agent.id,
            session_id=session.id,
            task_id=task.id,
            kind="text",
            body=f"Tarea #{task.id} '{task.name}' lista para revisión humana (approval gate).",
            status="open",
        )
        db.add(inbox)
    else:
        task.status = "done"
        _append_event(session, events, "agentos.done", "Task marked done")

    session.summary = summary
    session.status = "destroyed"
    session.ended_at = _now()
    _append_event(session, events, "session.destroy", "Ephemeral session destroyed")
    db.commit()
    db.refresh(session)
    return session


def _run_claude_stub(agent: Agent, task: Task) -> str:
    """Best-effort Anthropic Messages call (not full Agent SDK)."""
    import urllib.error
    import urllib.request
    import json

    api_key = os.environ["ANTHROPIC_API_KEY"]
    payload = {
        "model": agent.model if agent.model.startswith("claude") else "claude-sonnet-4-20250514",
        "max_tokens": 512,
        "system": agent.foundational_prompt + "\n\n" + agent.role_prompt,
        "messages": [
            {
                "role": "user",
                "content": f"Task: {task.name}\n\n{task.description or ''}\n\n"
                "Produce a short completion summary (no real tools available in this stub).",
            }
        ],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    parts = data.get("content") or []
    text = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
    return text or json.dumps(data)[:500]
