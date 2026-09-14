"""Phase 7 slice 1: Activity feed list/POST + SSE heartbeat stub."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.activity import ActivityEvent
from app.services.activity import append_activity, list_activity
from app.services.automations import create_automation, tick_automations
from app.services.seed import ensure_seed_agents_and_grants, seed_if_empty
from app.services.triggers import handle_webhook_trigger
from app.schemas.automation import AutomationAction, AutomationCreate
from app.schemas.trigger import WebhookTriggerIn

TEST_SECRET = "test-webhook-secret-phase7"


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


def _client(db):
    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    return TestClient(app)


def test_append_and_list_activity():
    db, _engine = _memory_db()
    try:
        row = append_activity(
            db, type="test.manual", message="hello activity", commit=True
        )
        assert row.id > 0
        rows = list_activity(db, limit=10)
        assert len(rows) >= 1
        assert rows[0].type == "test.manual"
        assert rows[0].message == "hello activity"
    finally:
        db.close()
        app.dependency_overrides.clear()


def test_http_post_and_get_activity():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        r = client.post(
            "/api/v1/activity",
            json={"type": "test.http", "message": "from POST"},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["type"] == "test.http"
        assert body["id"] > 0

        r2 = client.get("/api/v1/activity?limit=5")
        assert r2.status_code == 200
        items = r2.json()
        assert any(i["type"] == "test.http" for i in items)
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_task_create_emits_activity():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        r = client.post("/api/v1/tasks", json={"name": "activity-task"})
        assert r.status_code == 201, r.text
        task_id = r.json()["id"]

        items = client.get("/api/v1/activity").json()
        match = [i for i in items if i["type"] == "task.created" and i["task_id"] == task_id]
        assert len(match) == 1
        assert "activity-task" in match[0]["message"]
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_webhook_emits_activity(monkeypatch):
    monkeypatch.setenv("GALLAIA_WEBHOOK_SECRET", TEST_SECRET)
    get_settings.cache_clear()
    db, _engine = _memory_db()
    try:
        out = handle_webhook_trigger(
            db,
            settings=get_settings(),
            secret_header=TEST_SECRET,
            body=WebhookTriggerIn(shape="generic", name="wh-act"),
        )
        rows = list(
            db.scalars(
                select(ActivityEvent).where(ActivityEvent.type == "webhook.received")
            ).all()
        )
        assert len(rows) == 1
        assert rows[0].task_id == out.task_id
        assert rows[0].session_id == out.session_id
    finally:
        db.close()
        get_settings.cache_clear()


def test_automation_fire_emits_activity():
    db, _engine = _memory_db()
    try:
        create_automation(
            db,
            AutomationCreate(
                name="act-feed-auto",
                interval_minutes=1,
                enabled=True,
                action=AutomationAction(
                    type="create_task",
                    name="auto-task-act",
                    assignee_agent="default",
                ),
            ),
        )
        tick = tick_automations(db)
        assert tick.fired_count == 1
        rows = list(
            db.scalars(
                select(ActivityEvent).where(ActivityEvent.type == "automation.fired")
            ).all()
        )
        assert len(rows) == 1
        assert rows[0].automation_id == tick.fired_automation_ids[0]
        assert rows[0].task_id == tick.task_ids[0]
    finally:
        db.close()


def test_sse_stream_heartbeat_and_end():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        # Short stream: heartbeats + end within ~0.4s
        with client.stream(
            "GET",
            "/api/v1/activity/stream",
            params={"heartbeat_seconds": 0.1, "max_seconds": 0.35},
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")
            text = "".join(resp.iter_text())
        assert "event: heartbeat" in text
        assert "event: end" in text
        assert "max_seconds" in text
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_sse_receives_posted_activity():
    """POST while stream is open should deliver an activity SSE frame.

    Uses a background thread to POST after the stream starts; stream ends via max_seconds.
    """
    import threading
    import time

    db, _engine = _memory_db()
    client = _client(db)
    posted = {"ok": False}

    def _post_later():
        time.sleep(0.08)
        r = client.post(
            "/api/v1/activity",
            json={"type": "sse.probe", "message": "live event"},
        )
        posted["ok"] = r.status_code == 201

    try:
        t = threading.Thread(target=_post_later, daemon=True)
        t.start()
        with client.stream(
            "GET",
            "/api/v1/activity/stream",
            params={"heartbeat_seconds": 0.5, "max_seconds": 0.6},
        ) as resp:
            text = "".join(resp.iter_text())
        t.join(timeout=2)
        assert posted["ok"]
        assert "event: activity" in text
        assert "sse.probe" in text
    finally:
        app.dependency_overrides.clear()
        db.close()
