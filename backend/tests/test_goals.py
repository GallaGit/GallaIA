"""Phase 4 Goals foundation: DoD approve gate + spawn stub."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import Base
from app.db.session import get_db
from app.exceptions import BadRequestError
from app.main import app
from app.models import AgentSession, Task
from app.models.goal import Goal
from app.schemas.goal import GoalCreate
from app.services.goals import approve_goal, create_goal, get_goal, spawn_goal
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
