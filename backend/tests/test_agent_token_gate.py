"""Phase 3: agent token cannot mark a gated step done."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import Actor, parse_actor_headers
from app.db.base import Base
from app.db.session import get_db
from app.exceptions import BadRequestError, ForbiddenError
from app.main import app
from app.models import Agent, Project, Task
from app.services.authz import assert_actor_may_mark_done
from app.services.seed import ensure_seed_agents_and_grants, seed_if_empty
from app.services.templates import (
    DEMO_TWO_STEP_SLUG,
    get_template,
    instantiate_template,
)


def _memory_db():
    # StaticPool: one shared in-memory connection (needed for TestClient + commit/refresh)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
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
    return db, engine


def test_parse_actor_defaults_to_human():
    actor = parse_actor_headers(None, None)
    assert actor.is_human
    assert actor.agent_id is None


def test_parse_actor_agent_with_id():
    actor = parse_actor_headers("agent", "42")
    assert actor.is_agent
    assert actor.agent_id == 42


def test_parse_actor_rejects_invalid_type():
    with pytest.raises(BadRequestError):
        parse_actor_headers("robot", None)


def test_agent_denied_marking_approval_gated_done():
    db, _engine = _memory_db()
    try:
        template = get_template(db, DEMO_TWO_STEP_SLUG)
        result = instantiate_template(db, template)
        t1 = db.get(Task, result.tasks[0].id)
        assert t1 is not None
        assert t1.approval_gate is True

        agent = Actor(type="agent", agent_id=1)
        with pytest.raises(ForbiddenError) as denied:
            assert_actor_may_mark_done(db, t1, agent)
        assert "approval-gated" in denied.value.message.lower()
        assert denied.value.status_code == 403
    finally:
        db.close()


def test_human_allowed_marking_approval_gated_done():
    db, _engine = _memory_db()
    try:
        template = get_template(db, DEMO_TWO_STEP_SLUG)
        result = instantiate_template(db, template)
        t1 = db.get(Task, result.tasks[0].id)
        assert t1 is not None
        assert t1.approval_gate is True

        human = Actor(type="human")
        assert_actor_may_mark_done(db, t1, human)  # no raise
        t1.status = "done"
        db.commit()
        assert t1.status == "done"
    finally:
        db.close()


def test_agent_denied_marking_done_with_unmet_dependency():
    db, _engine = _memory_db()
    try:
        template = get_template(db, DEMO_TWO_STEP_SLUG)
        result = instantiate_template(db, template)
        t2 = db.get(Task, result.tasks[1].id)
        assert t2 is not None
        assert t2.depends_on_task_id is not None
        assert t2.approval_gate is False

        agent = Actor(type="agent", agent_id=1)
        with pytest.raises(ForbiddenError) as denied:
            assert_actor_may_mark_done(db, t2, agent)
        assert "unmet dependency" in denied.value.message.lower()
    finally:
        db.close()


def test_agent_may_mark_ungated_done_after_prior():
    """After human clears gate, agent can complete non-gated follow-up."""
    db, _engine = _memory_db()
    try:
        template = get_template(db, DEMO_TWO_STEP_SLUG)
        result = instantiate_template(db, template)
        t1 = db.get(Task, result.tasks[0].id)
        t2 = db.get(Task, result.tasks[1].id)
        assert t1 is not None and t2 is not None

        t1.status = "done"
        db.commit()

        agent = Actor(type="agent", agent_id=t2.assignee_agent_id)
        assert_actor_may_mark_done(db, t2, agent)  # no raise
    finally:
        db.close()


def test_patch_status_agent_403_human_200():
    """HTTP: X-Actor-Type agent -> 403 on gated done; human -> 200."""
    db, engine = _memory_db()

    def _override_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_db
    try:
        template = get_template(db, DEMO_TWO_STEP_SLUG)
        result = instantiate_template(db, template)
        task_id = result.tasks[0].id
        assert result.tasks[0].approval_gate is True

        with TestClient(app, raise_server_exceptions=True) as client:
            denied = client.patch(
                f"/api/v1/tasks/{task_id}/status",
                json={"status": "done"},
                headers={"X-Actor-Type": "agent", "X-Agent-Id": "1"},
            )
            assert denied.status_code == 403, denied.text
            assert denied.json()["error"]["code"] == "forbidden"
            task = db.get(Task, task_id)
            assert task is not None
            db.refresh(task)
            assert task.status == "todo"

            allowed = client.patch(
                f"/api/v1/tasks/{task_id}/status",
                json={"status": "done"},
                headers={"X-Actor-Type": "human"},
            )
            assert allowed.status_code == 200, allowed.text
            assert allowed.json()["status"] == "done"
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()
