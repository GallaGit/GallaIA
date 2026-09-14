"""Isolation grants wall: default-deny + Front-only cannot use GitHub."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agentos.grants import GrantSet, evaluate_tool
from app.agentos.models import Task
from app.agentos.runner import SessionRunner
from app.agentos.seeds import get_seed, list_seeds
from app.agentos.store import AgentOSStore
from app.core.config import get_settings
from app.db.base import Base
from app.models import Agent, AgentGrant, Project
from app.models.task import Task as DbTask
from app.schemas.grant import GrantItem
from app.services.grants import grant_set_for_agent, grants_out, replace_agent_grants
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


def test_empty_grants_default_deny():
    grants = GrantSet()
    assert not grants.allows("mcp", "github")
    assert not grants.allows("mcp", "front")
    assert not grants.allows("repo", "GallaGit/GallaIA")
    assert not grants.allows("env", "GITHUB_TOKEN")
    denied = evaluate_tool(grants, "github.commit")
    assert denied.allowed is False
    assert denied.reason == "missing grant mcp:github"


def test_support_seed_is_front_only():
    seed = get_seed("support")
    grants = seed.grant_set()
    assert seed.mcp == ("front",)
    assert grants.allows("mcp", "front")
    assert not grants.allows("mcp", "github")
    assert not grants.allows("mcp", "agentos")
    assert not grants.allows("repo", "GallaGit/GallaIA")
    assert not grants.allows("env", "GITHUB_TOKEN")
    names = {s.name for s in list_seeds()}
    assert "support" in names


def test_support_mock_allows_front_denies_github(monkeypatch):
    _clear_llm_env(monkeypatch)
    store = AgentOSStore()
    task = store.create_task(
        Task(name="Reset password", description="Front ticket", assignee_agent="support")
    )
    result = SessionRunner(store).run(task.id, runner="mock")
    events = {e.name: e for e in result.tool_events}
    front = events["front.list_conversations"]
    assert front.output.get("ok") is True
    assert front.output.get("denied") is not True
    github = events["github.commit"]
    assert github.output.get("ok") is False
    assert github.output.get("denied") is True
    assert github.output.get("missing_grant") == {"kind": "mcp", "name": "github"}
    assert "must-not-land" not in str(github.output)


def test_senior_dev_github_commit_allowed(monkeypatch):
    _clear_llm_env(monkeypatch)
    store = AgentOSStore()
    task = store.create_task(Task(name="Fix bug", assignee_agent="senior-dev"))
    result = SessionRunner(store).run(task.id, runner="mock")
    github = next(e for e in result.tool_events if e.name == "github.commit")
    assert github.output.get("ok") is True
    assert github.output.get("denied") is not True
    assert github.output.get("sha") == "mockdeadbeef"


def test_sqlite_support_seed_and_grant_api():
    db = _memory_db()
    try:
        support = db.scalar(select(Agent).where(Agent.name == "support"))
        assert support is not None
        grants = grant_set_for_agent(support)
        assert grants.allows("mcp", "front")
        assert not grants.allows("mcp", "github")
        listed = grants_out(support)
        assert listed.agent_name == "support"
        assert {"kind": "mcp", "name": "front"} in [
            g.model_dump() for g in listed.grants
        ]

        replace_agent_grants(
            db,
            support,
            [GrantItem(kind="mcp", name="front"), GrantItem(kind="mcp", name="inbox")],
        )
        db.refresh(support)
        updated = grant_set_for_agent(support)
        assert updated.allows("mcp", "inbox")
        assert not updated.allows("mcp", "github")

        replace_agent_grants(db, support, [])
        db.refresh(support)
        assert grant_set_for_agent(support).items == frozenset()
        assert db.scalar(select(AgentGrant).where(AgentGrant.agent_id == support.id)) is None
    finally:
        db.close()


def test_sqlite_mock_runner_support_cannot_github(monkeypatch):
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
        details = [row.get("detail", "") for row in session.get_tool_events()]
        tools = [row.get("tool") for row in session.get_tool_events()]
        assert "front.list_conversations" in tools
        assert "github.commit" in tools
        github_detail = next(
            row["detail"]
            for row in session.get_tool_events()
            if row.get("tool") == "github.commit"
        )
        assert "DENIED" in github_detail
        assert "mcp:github" in github_detail
        front_detail = next(
            row["detail"]
            for row in session.get_tool_events()
            if row.get("tool") == "front.list_conversations"
        )
        assert "DENIED" not in front_detail
        assert details  # session recorded events
    finally:
        db.close()
