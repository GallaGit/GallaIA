"""Phase 5 slice 2: named interval automations + test-clock tick."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import AgentSession, Task
from app.models.automation import Automation
from app.schemas.automation import AutomationAction, AutomationCreate
from app.services.automations import (
    create_automation,
    is_due,
    tick_automations,
)
from app.services.seed import ensure_seed_agents_and_grants, seed_if_empty

def _as_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)



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


def _make_automation(
    db,
    *,
    name: str = "hourly-demo",
    interval_minutes: int = 60,
    enabled: bool = True,
    last_fired_at: datetime | None = None,
    task_name: str = "auto-task",
) -> Automation:
    row = create_automation(
        db,
        AutomationCreate(
            name=name,
            interval_minutes=interval_minutes,
            enabled=enabled,
            action=AutomationAction(
                type="create_task",
                name=task_name,
                description="from test",
                assignee_agent="default",
            ),
        ),
    )
    if last_fired_at is not None:
        row.last_fired_at = last_fired_at
        db.commit()
        db.refresh(row)
    return row


def test_not_due_when_interval_not_elapsed():
    db, _engine = _memory_db()
    try:
        clock = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
        # Fired 10 minutes ago; interval 60 → not due
        auto = _make_automation(
            db,
            last_fired_at=clock - timedelta(minutes=10),
            interval_minutes=60,
        )
        assert is_due(auto, clock) is False

        result = tick_automations(db, now=clock)
        assert result.fired_count == 0
        assert result.fired_automation_ids == []
        assert result.task_ids == []
        assert result.session_ids == []

        db.refresh(auto)
        assert _as_utc(auto.last_fired_at) == clock - timedelta(minutes=10)
        tasks = list(db.scalars(select(Task).where(Task.name == "auto-task")).all())
        assert tasks == []
    finally:
        db.close()


def test_due_on_test_clock_creates_task_and_session():
    db, _engine = _memory_db()
    try:
        clock = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
        # Never fired → due on first tick
        auto = _make_automation(db, name="first-fire", last_fired_at=None)

        result = tick_automations(db, now=clock)
        assert result.fired_count == 1
        assert result.fired_automation_ids == [auto.id]
        assert len(result.task_ids) == 1
        assert len(result.session_ids) == 1

        db.refresh(auto)
        assert _as_utc(auto.last_fired_at) == clock

        task = db.get(Task, result.task_ids[0])
        assert task is not None
        assert task.name == "auto-task"
        assert task.status == "todo"
        assert task.assignee_agent_id is not None

        stub = db.get(AgentSession, result.session_ids[0])
        assert stub is not None
        assert stub.task_id == task.id
        assert stub.runner == "automation"
        assert stub.status == "queued"
    finally:
        db.close()


def test_due_when_interval_elapsed_after_last_fire():
    db, _engine = _memory_db()
    try:
        clock = datetime(2026, 9, 15, 14, 0, tzinfo=timezone.utc)
        auto = _make_automation(
            db,
            name="elapsed",
            interval_minutes=30,
            last_fired_at=clock - timedelta(minutes=30),
            task_name="elapsed-task",
        )
        assert is_due(auto, clock) is True

        result = tick_automations(db, now=clock)
        assert result.fired_count == 1
        assert result.task_ids
        task = db.get(Task, result.task_ids[0])
        assert task is not None
        assert task.name == "elapsed-task"
    finally:
        db.close()


def test_disabled_automation_does_not_fire():
    db, _engine = _memory_db()
    try:
        clock = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
        auto = _make_automation(db, name="off", enabled=False, last_fired_at=None)
        result = tick_automations(db, now=clock)
        assert result.fired_count == 0
        db.refresh(auto)
        assert auto.last_fired_at is None
    finally:
        db.close()


def test_http_crud_and_tick():
    db, engine = _memory_db()

    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    try:
        client = TestClient(app)
        # Create
        resp = client.post(
            "/api/v1/automations",
            json={
                "name": "http-auto",
                "interval_minutes": 15,
                "enabled": True,
                "action": {
                    "type": "create_task",
                    "name": "http-task",
                    "assignee_agent": "default",
                },
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        auto_id = body["id"]
        assert body["name"] == "http-auto"
        assert body["interval_minutes"] == 15
        assert body["action"]["type"] == "create_task"

        # List
        listed = client.get("/api/v1/automations")
        assert listed.status_code == 200
        assert any(a["id"] == auto_id for a in listed.json())

        # Get
        got = client.get(f"/api/v1/automations/{auto_id}")
        assert got.status_code == 200
        assert got.json()["id"] == auto_id

        # Tick with test clock — never fired → due
        clock = "2026-09-15T12:00:00+00:00"
        tick = client.post("/api/v1/automations/tick", json={"now": clock})
        assert tick.status_code == 200, tick.text
        report = tick.json()
        assert report["fired_count"] == 1
        assert report["fired_automation_ids"] == [auto_id]
        assert len(report["task_ids"]) == 1
        assert len(report["session_ids"]) == 1

        # Immediate re-tick same clock → not due
        tick2 = client.post("/api/v1/automations/tick", json={"now": clock})
        assert tick2.status_code == 200
        assert tick2.json()["fired_count"] == 0

        # Patch disable
        patched = client.patch(
            f"/api/v1/automations/{auto_id}",
            json={"enabled": False},
        )
        assert patched.status_code == 200
        assert patched.json()["enabled"] is False

        # Delete
        deleted = client.delete(f"/api/v1/automations/{auto_id}")
        assert deleted.status_code == 204
        assert client.get(f"/api/v1/automations/{auto_id}").status_code == 404
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()
