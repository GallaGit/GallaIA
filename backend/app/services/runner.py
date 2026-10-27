"""
Task runner: mock by default; LLM through the F2.1 gateway when keys are set.

Phase 1 MVP: simulated session that updates DB and emits fake tool events.
F2.1b: the LLM call goes through `app.llm.gateway` (OpenRouter -> Groq -> mock)
with the agent's own model and one `llm_usage` row per attempt.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.agentos.filesystem import evaluate_fs
from app.agentos.grants import evaluate_tool
from app.agentos.network import evaluate_http
from app.models import Agent, AgentSession, InboxMessage, Task
from app.llm import gateway
from app.llm.usage import db_usage_sink
from app.services.filesystem import filesystem_acl_for_agent
from app.services.grants import grant_set_for_agent
from app.services.network import network_policy_for_agent
from app.services.secrets import resolve_agent_secrets, secret_refs_for_agent
from app.core.security import Actor
from app.services.authz import assert_actor_may_mark_done
from app.services.templates import assert_prior_step_done


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


def _control_plane_runner(agent: Agent | None = None) -> str:
    """UI runner label: first configured gateway provider, else mock.

    An agent whose model is `mock` always runs the mock path.
    """
    if agent is not None and gateway.resolve_model(agent.model)[0] == gateway.MOCK:
        return "mock"
    providers = gateway.configured_providers()
    if agent is not None:
        providers = gateway.providers_for_model(agent.model, providers)
    if providers:
        return providers[0].name
    return "mock"


def run_task_session(db: Session, task: Task, agent: Agent) -> AgentSession:
    """Start a (mock or LLM) session for a task and update status."""
    assert_prior_step_done(db, task)
    runner_name = _control_plane_runner(agent)
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

    if runner_name != "mock":
        summary = _run_gateway(db, session, events, agent, task)
    else:
        summary = (
            f"[mock] Agent '{agent.name}' completed task '{task.name}'. "
            "Set OPENROUTER_API_KEY (or GROQ_API_KEY) for an optional LLM stub."
        )
        _append_event(session, events, "mock.think", "Simulating tool use…")
        _append_event(session, events, "mock.write", "Would write via filesystem MCP")
        if agent.name == "fe":
            _append_gated(
                session,
                events,
                grants,
                "agentos.task.write_activity",
                "FE UI progress",
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
                "https://registry.npmjs.org/react",
                "npm registry HTTP",
            )
            _append_http(
                session,
                events,
                network,
                "https://api.github.com/user",
                "must not succeed outside allowlist",
            )
            _append_fs(session, events, filesystem, "read", "/agents/fe/ui.md")
            _append_fs(
                session, events, filesystem, "read", "/agents/be/api.md"
            )
            _append_fs(
                session,
                events,
                filesystem,
                "read",
                "/agents/fe/../be/api.md",
            )
            for secret_name in secret_runtime.values:
                _append_event(
                    session,
                    events,
                    "secret.get",
                    f"name={secret_name} present=true",
                )
        elif agent.name == "be":
            _append_gated(
                session,
                events,
                grants,
                "github.commit",
                f"feat: {task.name} (mock)",
            )
            _append_fs(
                session, events, filesystem, "read", "/agents/be/api.md"
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
        # Run path is always an agent actor — refuse gated done (belt + suspenders).
        assert_actor_may_mark_done(
            db, task, Actor(type="agent", agent_id=agent.id)
        )
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


def _run_gateway(
    db: Session,
    session: AgentSession,
    events: list,
    agent: Agent,
    task: Task,
) -> str:
    """Best-effort chat completion via the gateway (not full Agent SDK).

    Uses the agent's model, records usage on `db` (committed with the session)
    and logs one tool event per failed provider. If every provider fails, the
    gateway's mock fallback produces the summary.
    """
    from app.services.untrusted import UNTRUSTED_NOTICE, wrap_untrusted

    mock_summary = (
        f"[mock] Agent '{agent.name}' completed task '{task.name}' "
        "(all LLM providers failed)."
    )
    system = agent.foundational_prompt + "\n\n" + agent.role_prompt + "\n\n" + UNTRUSTED_NOTICE
    user_content = (
        wrap_untrusted(f"Task: {task.name}\n\n{task.description or ''}", "task")
        + "\n\nProduce a short completion summary (no real tools available in this stub)."
    )
    result = gateway.complete(
        system,
        user_content,
        model=agent.model,
        fallback=lambda _system, _user: mock_summary,
        on_usage=db_usage_sink(
            db, source="session", agent=agent.name, session_id=session.id
        ),
    )
    for attempt in result.attempts:
        if not attempt.ok:
            _append_event(
                session, events, f"{attempt.provider}.error", attempt.error or "error"
            )
    session.runner = result.provider
    if result.provider == gateway.MOCK:
        _append_event(
            session, events, "llm.fallback", "All providers failed; mock summary"
        )
        return mock_summary
    _append_event(
        session,
        events,
        f"{result.provider}.chat.completions",
        (
            f"Completed {result.provider} call ({result.model}) "
            f"in={result.input_tokens} out={result.output_tokens} "
            f"latency_ms={result.latency_ms}"
        ),
    )
    return result.text
