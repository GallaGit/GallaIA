"""Isolation network wall: limited allowlist denies hosts outside the list."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agentos.models import Task
from app.agentos.network import NetworkPolicy, evaluate_http, gated_http_output
from app.agentos.runner import SessionRunner
from app.agentos.seeds import get_seed
from app.agentos.store import AgentOSStore
from app.core.config import get_settings
from app.db.base import Base
from app.models import Agent, AgentNetworkPolicy, Project
from app.models.task import Task as DbTask
from app.services.network import network_out, network_policy_for_agent, replace_agent_network
from app.services.runner import run_task_session
from app.services.seed import ensure_seed_agents_and_grants, seed_if_empty


def _clear_llm_env(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    get_settings.cache_clear()


def _memory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _sqlite_fk(dbapi_conn, _connection_record):  # noqa: ANN001
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = Session()
    seed_if_empty(db)
    ensure_seed_agents_and_grants(db)
    return db


def test_open_allows_any_host():
    policy = NetworkPolicy.open()
    assert policy.allows_host("https://api.github.com/repos/x")
    assert policy.allows_host("evil.example")
    assert policy.allows_host("")
    decision = evaluate_http(policy, "https://api.github.com/user")
    assert decision.allowed is True


def test_limited_denies_host_outside_allowlist():
    policy = NetworkPolicy.limited(["api.front.com"])
    assert policy.allows_host("https://API.Front.COM/conversations")
    assert policy.allows_host("https://api.front.com:443/v1")
    assert not policy.allows_host("https://api.github.com/repos/GallaGit/GallaIA")
    assert not policy.allows_host("evil.example")
    denied = gated_http_output(
        policy, "https://api.github.com/user", {"status": 200, "must-not-land": True}
    )
    assert denied["ok"] is False
    assert denied["denied"] is True
    assert "api.github.com" in denied["reason"]
    assert "must-not-land" not in str(denied)
    allowed = gated_http_output(
        policy, "https://api.front.com/conversations", {"status": 200, "source": "fake-front"}
    )
    assert allowed["ok"] is True
    assert allowed.get("denied") is not True
    assert allowed["source"] == "fake-front"


def test_limited_empty_allowlist_denies_all():
    policy = NetworkPolicy.limited([])
    assert not policy.allows_host("https://api.front.com/x")
    missing = evaluate_http(policy, "")
    assert missing.allowed is False
    assert "missing host" in missing.reason


def test_support_seed_is_limited_front_host():
    seed = get_seed("support")
    policy = seed.network_policy()
    assert seed.network_mode == "limited"
    assert seed.network_allowlist == ("api.front.com",)
    assert policy.mode == "limited"
    assert policy.allows_host("https://api.front.com/conversations")
    assert not policy.allows_host("https://api.github.com/user")
    assert get_seed("senior-dev").network_policy().mode == "open"


def test_support_mock_fetch_denies_github_host(monkeypatch):
    _clear_llm_env(monkeypatch)
    store = AgentOSStore()
    task = store.create_task(
        Task(name="Reset password", description="Front ticket", assignee_agent="support")
    )
    result = SessionRunner(store).run(task.id, runner="mock")
    fetches = [e for e in result.tool_events if e.name == "http.fetch"]
    assert len(fetches) == 2
    by_url = {e.input["url"]: e for e in fetches}
    front = by_url["https://api.front.com/conversations"]
    assert front.output.get("ok") is True
    assert front.output.get("denied") is not True
    github = by_url["https://api.github.com/repos/GallaGit/GallaIA"]
    assert github.output.get("ok") is False
    assert github.output.get("denied") is True
    assert github.output.get("network", {}).get("host") == "api.github.com"
    assert "must-not-land" not in str(github.output)


def test_open_mock_fetch_allows_github(monkeypatch):
    _clear_llm_env(monkeypatch)
    store = AgentOSStore()
    task = store.create_task(Task(name="Probe", assignee_agent="senior-dev"))
    result = SessionRunner(store).run(task.id, runner="mock")
    fetches = [e for e in result.tool_events if e.name == "http.fetch"]
    assert len(fetches) == 1
    assert fetches[0].input["url"] == "https://api.github.com/repos/GallaGit/GallaIA"
    assert fetches[0].output.get("ok") is True
    assert fetches[0].output.get("denied") is not True
    assert fetches[0].output.get("sha") == "mockdeadbeef"


def test_sqlite_support_network_api():
    db = _memory_db()
    try:
        support = db.scalar(select(Agent).where(Agent.name == "support"))
        assert support is not None
        policy = network_policy_for_agent(support)
        assert policy.mode == "limited"
        assert "api.front.com" in policy.allowlist
        assert not policy.allows_host("https://api.github.com/user")
        listed = network_out(support)
        assert listed.agent_name == "support"
        assert listed.mode == "limited"
        assert listed.allowlist == ["api.front.com"]

        replace_agent_network(db, support, "limited", ["api.front.com", "https://hooks.front.com/x"])
        db.refresh(support)
        updated = network_policy_for_agent(support)
        assert updated.allows_host("hooks.front.com")
        assert not updated.allows_host("api.github.com")

        replace_agent_network(db, support, "open", [])
        db.refresh(support)
        opened = network_policy_for_agent(support)
        assert opened.mode == "open"
        assert opened.allows_host("https://api.github.com/user")
        row = db.get(AgentNetworkPolicy, support.id)
        assert row is not None
        assert row.mode == "open"
    finally:
        db.close()


def test_sqlite_mock_runner_support_cannot_fetch_github(monkeypatch):
    _clear_llm_env(monkeypatch)
    db = _memory_db()
    try:
        project = db.scalar(select(Project).where(Project.slug == "default"))
        support = db.scalar(select(Agent).where(Agent.name == "support"))
        task = DbTask(
            project_id=project.id,
            name="Front ticket",
            assignee_agent_id=support.id,
            status="todo",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        session = run_task_session(db, task, support)
        http_events = [
            row for row in session.get_tool_events() if row.get("tool") == "http.fetch"
        ]
        assert len(http_events) == 2
        details = [row.get("detail", "") for row in http_events]
        assert any("api.front.com" in d and "DENIED" not in d for d in details)
        github_detail = next(d for d in details if "api.github.com" in d)
        assert "DENIED" in github_detail
        assert "not allowlisted" in github_detail
    finally:
        db.close()
