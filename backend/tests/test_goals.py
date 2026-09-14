"""Phase 4 Goals: DoD approve + spawn + orchestrator stub + safety rails."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import Base
from app.db.session import get_db
from app.exceptions import BadRequestError, ForbiddenError
from app.main import app
from app.models import Agent, AgentSession, Task
from app.models.goal import Goal
from app.schemas.goal import GoalCreate
from app.services.goals import (
    approve_goal,
    create_goal,
    get_goal,
    orchestrate_goal,
    spawn_goal,
)
from app.services.seed import ensure_seed_agents_and_grants, seed_if_empty


def _memory_db():
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


def test_create_goal_starts_draft_with_dod_items():
    db, _engine = _memory_db()
    try:
        goal = create_goal(
            db,
            GoalCreate(name="Ship feature X", dod_items=["PR open", "Tests green"]),
        )
        assert goal.status == "draft"
        assert goal.approved_at is None
        assert goal.get_dod_items() == ["PR open", "Tests green"]
        assert goal.get_dod_checked() == [False, False]
        assert goal.spend_cap is None
        assert goal.stuck_threshold == 19
        out_items = get_goal(db, goal.id).get_dod_items()
        assert out_items == ["PR open", "Tests green"]
    finally:
        db.close()


def test_create_goal_rejects_empty_dod():
    db, _engine = _memory_db()
    try:
        with pytest.raises(BadRequestError):
            create_goal(db, GoalCreate(name="Bad", dod_items=["  ", ""]))
    finally:
        db.close()


def test_cannot_spawn_unapproved_goal():
    db, _engine = _memory_db()
    try:
        goal = create_goal(
            db,
            GoalCreate(name="Needs approve", dod_items=["Item A", "Item B"]),
        )
        assert goal.status == "draft"
        with pytest.raises(BadRequestError) as exc:
            spawn_goal(db, goal.id)
        assert "not approved" in str(exc.value.message).lower() or "approve" in str(
            exc.value.message
        ).lower()
        sessions = list(db.scalars(select(AgentSession)).all())
        assert sessions == []
    finally:
        db.close()


def test_approve_then_spawn_creates_session_and_task_link():
    db, _engine = _memory_db()
    try:
        goal = create_goal(
            db,
            GoalCreate(name="Approved path", dod_items=["DoD 1", "DoD 2"]),
        )
        approved = approve_goal(db, goal.id)
        assert approved.status == "approved"
        assert approved.approved_at is not None

        result = spawn_goal(db, goal.id)
        assert result.goal_id == goal.id
        assert result.goal_status == "active"
        assert result.session_id > 0
        assert result.task_id is not None

        stub = db.get(AgentSession, result.session_id)
        assert stub is not None
        assert stub.goal_id == goal.id
        assert stub.task_id == result.task_id
        assert stub.runner == "goal-spawn"
        assert stub.status == "queued"

        task = db.get(Task, result.task_id)
        assert task is not None
        assert f"goal:{goal.id}" in task.name

        db.refresh(goal)
        assert goal.status == "active"
        assert goal.activated_at is not None
        assert float(goal.spend_accrued) >= 1.0
    finally:
        db.close()


def test_orchestrate_two_item_dod_completes_via_two_sessions():
    """Phase 4 done-when: 2-item DoD completes via ≥2 specialist sessions."""
    db, _engine = _memory_db()
    try:
        goal = create_goal(
            db,
            GoalCreate(name="Two step", dod_items=["Spec done", "PR open"]),
        )
        approve_goal(db, goal.id)
        first = spawn_goal(db, goal.id)
        assert first.goal_status == "active"

        step1 = orchestrate_goal(db, goal.id)
        assert step1.action == "spawned"
        assert step1.goal_status == "active"
        assert step1.dod_checked == [True, False]
        assert step1.session_id is not None
        assert step1.session_id != first.session_id

        step2 = orchestrate_goal(db, goal.id)
        assert step2.action == "done"
        assert step2.goal_status == "done"
        assert step2.dod_checked == [True, True]

        sessions = list(
            db.scalars(
                select(AgentSession).where(AgentSession.goal_id == goal.id)
            ).all()
        )
        assert len(sessions) >= 2
        db.refresh(goal)
        assert goal.status == "done"
        assert all(goal.get_dod_checked())
    finally:
        db.close()


def test_spend_cap_zero_rejects_spawn():
    db, _engine = _memory_db()
    try:
        goal = create_goal(
            db,
            GoalCreate(
                name="Zero cap",
                dod_items=["A", "B"],
                spend_cap=0.0,
            ),
        )
        approve_goal(db, goal.id)
        with pytest.raises(ForbiddenError) as exc:
            spawn_goal(db, goal.id)
        assert "spend_cap" in str(exc.value.message).lower()
        assert list(db.scalars(select(AgentSession)).all()) == []
    finally:
        db.close()


def test_spend_cap_zero_rejects_orchestrate():
    db, _engine = _memory_db()
    try:
        # Create with positive cap so spawn works, then clamp to 0.00
        goal = create_goal(
            db,
            GoalCreate(name="Cap later", dod_items=["A", "B"], spend_cap=10.0),
        )
        approve_goal(db, goal.id)
        spawn_goal(db, goal.id)
        db.refresh(goal)
        goal.spend_cap = 0.0
        db.commit()

        with pytest.raises(ForbiddenError):
            orchestrate_goal(db, goal.id)
    finally:
        db.close()


def test_stuck_identical_summaries_stops():
    db, _engine = _memory_db()
    try:
        goal = create_goal(
            db,
            GoalCreate(
                name="Stuck loop",
                dod_items=["Keep going", "Still going", "Done someday"],
                stuck_threshold=2,
            ),
        )
        approve_goal(db, goal.id)
        spawn_goal(db, goal.id)
        db.refresh(goal)

        agent = db.scalar(select(Agent).order_by(Agent.id).limit(1))
        assert agent is not None
        # Force last 2 sessions to share an identical summary
        for sess in db.scalars(
            select(AgentSession).where(AgentSession.goal_id == goal.id)
        ).all():
            sess.summary = "IDENTICAL_STUCK_SUMMARY"
            sess.status = "completed"
        twin = AgentSession(
            agent_id=agent.id,
            task_id=None,
            goal_id=goal.id,
            runner="goal-orchestrate",
            status="completed",
            summary="IDENTICAL_STUCK_SUMMARY",
            tool_call_log="[]",
        )
        db.add(twin)
        db.commit()

        out = orchestrate_goal(db, goal.id)
        assert out.action == "stuck"
        assert out.goal_status == "stuck"
        db.refresh(goal)
        assert goal.status == "stuck"
    finally:
        db.close()


def test_max_wall_seconds_rejects_orchestrate():
    db, _engine = _memory_db()
    try:
        goal = create_goal(
            db,
            GoalCreate(
                name="Wall clock",
                dod_items=["A", "B"],
                max_wall_seconds=60,
            ),
        )
        approve_goal(db, goal.id)
        spawn_goal(db, goal.id)
        db.refresh(goal)
        goal.activated_at = datetime.now(timezone.utc) - timedelta(seconds=120)
        db.commit()

        with pytest.raises(BadRequestError) as exc:
            orchestrate_goal(db, goal.id)
        assert "max_wall" in str(exc.value.message).lower() or "wall" in str(
            exc.value.message
        ).lower()
    finally:
        db.close()


def test_http_cannot_spawn_draft_returns_400():
    db, engine = _memory_db()

    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            created = client.post(
                "/api/v1/goals",
                json={"name": "HTTP draft", "dod_items": ["one", "two"]},
            )
            assert created.status_code == 201, created.text
            goal_id = created.json()["id"]
            assert created.json()["status"] == "draft"

            denied = client.post(f"/api/v1/goals/{goal_id}/spawn")
            assert denied.status_code == 400, denied.text
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()


def test_http_approve_then_spawn_201():
    db, engine = _memory_db()

    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            created = client.post(
                "/api/v1/goals",
                json={"name": "HTTP ok", "dod_items": ["a", "b"]},
            )
            assert created.status_code == 201, created.text
            goal_id = created.json()["id"]

            listed = client.get("/api/v1/goals")
            assert listed.status_code == 200
            assert any(g["id"] == goal_id for g in listed.json())

            got = client.get(f"/api/v1/goals/{goal_id}")
            assert got.status_code == 200
            assert got.json()["dod_items"] == ["a", "b"]
            assert got.json()["dod_checked"] == [False, False]

            approved = client.post(f"/api/v1/goals/{goal_id}/approve")
            assert approved.status_code == 200, approved.text
            assert approved.json()["status"] == "approved"

            spawned = client.post(f"/api/v1/goals/{goal_id}/spawn")
            assert spawned.status_code == 201, spawned.text
            body = spawned.json()
            assert body["goal_status"] == "active"
            assert body["session_id"] > 0
            assert body["task_id"] is not None
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()


def test_http_orchestrate_two_steps_and_spend_cap_403():
    db, engine = _memory_db()

    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            created = client.post(
                "/api/v1/goals",
                json={
                    "name": "HTTP orch",
                    "dod_items": ["alpha", "beta"],
                    "stuck_threshold": 19,
                },
            )
            assert created.status_code == 201, created.text
            goal_id = created.json()["id"]

            assert client.post(f"/api/v1/goals/{goal_id}/approve").status_code == 200
            spawn = client.post(f"/api/v1/goals/{goal_id}/spawn")
            assert spawn.status_code == 201, spawn.text

            o1 = client.post(f"/api/v1/goals/{goal_id}/orchestrate")
            assert o1.status_code == 200, o1.text
            assert o1.json()["action"] == "spawned"
            assert o1.json()["dod_checked"] == [True, False]

            o2 = client.post(f"/api/v1/goals/{goal_id}/orchestrate")
            assert o2.status_code == 200, o2.text
            assert o2.json()["action"] == "done"
            assert o2.json()["goal_status"] == "done"

            # spend_cap 0.00 → 403 on spawn
            capped = client.post(
                "/api/v1/goals",
                json={
                    "name": "Capped",
                    "dod_items": ["x", "y"],
                    "spend_cap": 0.0,
                },
            )
            assert capped.status_code == 201, capped.text
            cid = capped.json()["id"]
            assert client.post(f"/api/v1/goals/{cid}/approve").status_code == 200
            denied = client.post(f"/api/v1/goals/{cid}/spawn")
            assert denied.status_code == 403, denied.text
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()
