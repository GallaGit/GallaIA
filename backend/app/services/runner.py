"""
Task runner: mock by default; optional OpenRouter or Anthropic if keys are set.

Phase 1 MVP: simulated session that updates DB and emits fake tool events.
Real Agent SDK integration is optional and best-effort.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.agentos.filesystem import evaluate_fs
from app.agentos.grants import evaluate_tool
from app.agentos.network import evaluate_http
from app.models import Agent, AgentSession, InboxMessage, Task
from app.providers.openrouter import (
    complete as openrouter_complete,
    openrouter_api_key,
    openrouter_model,
)
from app.services.filesystem import filesystem_acl_for_agent
from app.services.grants import grant_set_for_agent
from app.services.network import network_policy_for_agent
from app.services.secrets import resolve_agent_secrets, secret_refs_for_agent


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


def _append_gated(
    session: AgentSession,
    events: list,
    grants,
    name: str,
    detail: str,
    tool_input: dict | None = None,
) -> bool:
    """Record a tool event; return False when default-deny blocked it."""
    decision = evaluate_tool(grants, name, tool_input)
    if decision.allowed:
        _append_event(session, events, name, detail)
        return True
    _append_event(
        session,
        events,
        name,
        f"DENIED {decision.reason}",
    )
    return False


def _append_http(
    session: AgentSession,
    events: list,
    policy,
    url: str,
    detail: str,
) -> bool:
    """Record a mock fetch; return False when limited policy blocked the host."""
    decision = evaluate_http(policy, url)
    if decision.allowed:
        _append_event(session, events, "http.fetch", f"{url} {detail}")
        return True
    _append_event(
        session,
        events,
        "http.fetch",
        f"DENIED {decision.reason} url={url}",
    )
    return False


def _append_fs(
    session: AgentSession,
    events: list,
    acl,
    op: str,
    path: str,
) -> bool:
    """Record a mock fs tool; return False when ACL blocked the path."""
    decision = evaluate_fs(acl, op, path)
    tool = f"fs.{op}"
    if decision.allowed:
        _append_event(session, events, tool, f"{path} ok")
        return True
    _append_event(
        session,
        events,
        tool,
        f"DENIED {decision.reason} path={path}",
    )
    return False


def _anthropic_key() -> str:
    try:
        from app.core.config import get_settings

        key = (get_settings().anthropic_api_key or "").strip()
        if key:
            return key
    except Exception:  # noqa: BLE001
        pass
    return (os.getenv("ANTHROPIC_API_KEY") or "").strip()


def _control_plane_runner() -> str:
    """UI runner: OpenRouter if keyed, else Anthropic, else mock."""
    if openrouter_api_key():
        return "openrouter"
    if _anthropic_key():
        return "claude"
    return "mock"


def run_task_session(db: Session, task: Task, agent: Agent) -> AgentSession:
    """Start a (mock or LLM) session for a task and update status."""
    runner_name = _control_plane_runner()
    grants = grant_set_for_agent(agent)
    network = network_policy_for_agent(agent)
    filesystem = filesystem_acl_for_agent(agent)
    secret_runtime = resolve_agent_secrets(agent)

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
    _append_event(
        session,
        events,
        "session.manifest",
        (
            f"grants={grants.as_list()} network={network.as_dict()} "
            f"fs={filesystem.as_list()} secrets={secret_refs_for_agent(agent).as_list()} "
            f"isolation=grants-default-deny+network-policy+fs-acl+secret-refs"
        ),
    )
    _append_event(
        session,
        events,
        "session.secrets",
        f"injected={secret_runtime.as_public_dict()}",
    )

    if runner_name == "openrouter":
        try:
            summary = _run_openrouter_stub(agent, task)
            _append_event(
                session,
                events,
                "openrouter.chat.completions",
                f"Completed OpenRouter call ({openrouter_model()})",
            )
        except Exception as exc:  # noqa: BLE001 — MVP: fall back to mock
            summary = f"OpenRouter call failed ({exc}); finished with mock summary."
            _append_event(session, events, "openrouter.error", str(exc))
    elif runner_name == "claude":
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
            "Set OPENROUTER_API_KEY (or ANTHROPIC_API_KEY) for an optional LLM stub."
        )
        _append_event(session, events, "mock.think", "Simulating tool use…")
        _append_event(session, events, "mock.write", "Would write via filesystem MCP")
        if agent.name == "support":
            _append_gated(
                session,
                events,
                grants,
                "front.list_conversations",
                "fake Front inbox",
            )
            _append_gated(
                session,
                events,
                grants,
                "github.commit",
                "must not succeed without mcp:github",
            )
            _append_http(
                session,
                events,
                network,
                "https://api.front.com/conversations",
                "fake Front HTTP",
            )
            _append_http(
                session,
                events,
                network,
                "https://api.github.com/user",
                "must not succeed outside allowlist",
            )
            _append_fs(session, events, filesystem, "read", "/agents/support/ticket.md")
            _append_fs(
                session, events, filesystem, "read", "/agents/senior-dev/notes.md"
            )
            _append_fs(
                session,
                events,
                filesystem,
                "read",
                "/agents/support/../senior-dev/notes.md",
            )
            for secret_name in secret_runtime.values:
                _append_event(
                    session,
                    events,
                    "secret.get",
                    f"name={secret_name} present=true",
                )
        elif agent.name == "senior-dev":
            _append_gated(
                session,
                events,
                grants,
                "github.commit",
                f"feat: {task.name} (mock)",
            )
            _append_fs(
                session, events, filesystem, "read", "/agents/senior-dev/notes.md"
            )
        _append_gated(
            session, events, grants, "agentos.task_update", "Marking task complete"
        )

    if task.approval_gate:
        task.status = "review"
        _append_gated(
            session, events, grants, "agentos.gate", "Approval gate → left in review"
        )
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
        _append_gated(session, events, grants, "agentos.done", "Task marked done")

    session.summary = summary
    session.status = "destroyed"
    session.ended_at = _now()
    _append_event(session, events, "session.destroy", "Ephemeral session destroyed")
    db.commit()
    db.refresh(session)
    session.runtime_secrets = secret_runtime  # in-memory only; not an ORM column
    return session


def _run_openrouter_stub(agent: Agent, task: Task) -> str:
    """Best-effort OpenRouter Chat Completions call (not full Agent SDK)."""
    result = openrouter_complete(
        system=agent.foundational_prompt + "\n\n" + agent.role_prompt,
        user=(
            f"Task: {task.name}\n\n{task.description or ''}\n\n"
            "Produce a short completion summary (no real tools available in this stub)."
        ),
    )
    return result.text


def _run_claude_stub(agent: Agent, task: Task) -> str:
    """Best-effort Anthropic Messages call (not full Agent SDK)."""
    import urllib.error
    import urllib.request
    import json

    api_key = _anthropic_key()
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
