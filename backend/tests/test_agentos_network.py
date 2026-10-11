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
    policy = NetworkPolicy.limited(["registry.npmjs.org"])
    assert policy.allows_host("https://registry.npmjs.org/react")
    assert policy.allows_host("https://REGISTRY.NPMJS.ORG/react")
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
        policy, "https://registry.npmjs.org/react", {"status": 200, "source": "npm"}
    )
    assert allowed["ok"] is True
    assert allowed.get("denied") is not True
    assert allowed["source"] == "npm"


def test_limited_empty_allowlist_denies_all():
    policy = NetworkPolicy.limited([])
    assert not policy.allows_host("https://registry.npmjs.org/x")
    missing = evaluate_http(policy, "")
    assert missing.allowed is False
    assert "missing host" in missing.reason


def test_fe_seed_is_limited_npm_host():
    seed = get_seed("fe")
    policy = seed.network_policy()
    assert seed.network_mode == "limited"
    assert seed.network_allowlist == ("registry.npmjs.org",)
    assert policy.mode == "limited"
    assert policy.allows_host("https://registry.npmjs.org/react")
    assert not policy.allows_host("https://api.github.com/user")
    assert get_seed("be").network_policy().mode == "open"
    assert get_seed("orquestador").network_policy().mode == "open"


def test_fe_mock_fetch_denies_github_host(monkeypatch):
    _clear_llm_env(monkeypatch)
    store = AgentOSStore()
    task = store.create_task(
        Task(name="UI polish", description="FE work", assignee_agent="fe")
    )
    result = SessionRunner(store).run(task.id, runner="mock")
    fetches = [e for e in result.tool_events if e.name == "http.fetch"]
    assert len(fetches) == 2
    by_url = {e.input["url"]: e for e in fetches}
    npm = by_url["https://registry.npmjs.org/react"]
    assert npm.output.get("ok") is True
    assert npm.output.get("denied") is not True
    github = by_url["https://api.github.com/repos/GallaGit/GallaIA"]
    assert github.output.get("ok") is False
    assert github.output.get("denied") is True
    assert github.output.get("network", {}).get("host") == "api.github.com"
    assert "must-not-land" not in str(github.output)


def test_open_mock_fetch_allows_github(monkeypatch):
    _clear_llm_env(monkeypatch)
    store = AgentOSStore()
    task = store.create_task(Task(name="Probe", assignee_agent="be"))
    result = SessionRunner(store).run(task.id, runner="mock")
    fetches = [e for e in result.tool_events if e.name == "http.fetch"]
    assert len(fetches) == 1
    assert fetches[0].input["url"] == "https://api.github.com/repos/GallaGit/GallaIA"
    assert fetches[0].output.get("ok") is True
    assert fetches[0].output.get("denied") is not True
    assert fetches[0].output.get("sha") == "mockdeadbeef"


def test_sqlite_fe_network_api():
    db = _memory_db()
    try:
        fe = db.scalar(select(Agent).where(Agent.name == "fe"))
        assert fe is not None
        policy = network_policy_for_agent(fe)
        assert policy.mode == "limited"
        assert "registry.npmjs.org" in policy.allowlist
        assert not policy.allows_host("https://api.github.com/user")
        listed = network_out(fe)
        assert listed.agent_name == "fe"
        assert listed.mode == "limited"
        assert listed.allowlist == ["registry.npmjs.org"]

        replace_agent_network(
            db, fe, "limited", ["registry.npmjs.org", "https://cdn.jsdelivr.net/x"]
        )
        db.refresh(fe)
        updated = network_policy_for_agent(fe)
        assert updated.allows_host("cdn.jsdelivr.net")
        assert not updated.allows_host("api.github.com")

        replace_agent_network(db, fe, "open", [])
        db.refresh(fe)
        opened = network_policy_for_agent(fe)
        assert opened.mode == "open"
        assert opened.allows_host("https://api.github.com/user")
        row = db.get(AgentNetworkPolicy, fe.id)
        assert row is not None
        assert row.mode == "open"
    finally:
        db.close()


def test_sqlite_mock_runner_fe_cannot_fetch_github(monkeypatch):
    _clear_llm_env(monkeypatch)
    db = _memory_db()
    try:
        project = db.scalar(select(Project).where(Project.slug == "default"))
        fe = db.scalar(select(Agent).where(Agent.name == "fe"))
        task = DbTask(
            project_id=project.id,
            name="FE ticket",
            assignee_agent_id=fe.id,
            status="todo",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        session = run_task_session(db, task, fe)
        http_events = [
            row for row in session.get_tool_events() if row.get("tool") == "http.fetch"
        ]
        assert len(http_events) == 2
        details = [row.get("detail", "") for row in http_events]
        assert any("registry.npmjs.org" in d and "DENIED" not in d for d in details)
        github_detail = next(d for d in details if "api.github.com" in d)
        assert "DENIED" in github_detail
        assert "not allowlisted" in github_detail
    finally:
        db.close()
