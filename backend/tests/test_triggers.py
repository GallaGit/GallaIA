"""Phase 5 Triggers slice 1: signed webhook -> task + session; bad secret -> 401."""

from __future__ import annotations

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
from app.exceptions import UnauthorizedError
from app.main import app
from app.models import Agent, AgentSession, Task
from app.schemas.trigger import WebhookTriggerIn
from app.services.seed import ensure_seed_agents_and_grants, seed_if_empty
from app.services.triggers import handle_webhook_trigger, verify_webhook_secret

TEST_SECRET = "test-webhook-secret-phase5"


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


def _set_secret(monkeypatch, value: str = TEST_SECRET) -> None:
    monkeypatch.setenv("GALLAIA_WEBHOOK_SECRET", value)
    get_settings.cache_clear()


def test_verify_rejects_missing_and_bad_secret(monkeypatch):
    _set_secret(monkeypatch)
    settings = get_settings()
    try:
        verify_webhook_secret(None, settings)
        assert False, "expected UnauthorizedError"
    except UnauthorizedError as exc:
        assert exc.status_code == 401

    try:
        verify_webhook_secret("wrong", settings)
        assert False, "expected UnauthorizedError"
    except UnauthorizedError as exc:
        assert exc.status_code == 401


def test_verify_rejects_when_secret_unconfigured(monkeypatch):
    monkeypatch.delenv("GALLAIA_WEBHOOK_SECRET", raising=False)
    monkeypatch.setenv("GALLAIA_WEBHOOK_SECRET", "")
    get_settings.cache_clear()
    settings = get_settings()
    try:
        verify_webhook_secret("anything", settings)
        assert False, "expected UnauthorizedError"
    except UnauthorizedError as exc:
        assert exc.status_code == 401
        assert "not configured" in exc.message.lower() or "invalid" in exc.message.lower()


def test_valid_secret_creates_task_and_session_stub(monkeypatch):
    _set_secret(monkeypatch)
    db, engine = _memory_db()
    try:
        out = handle_webhook_trigger(
            db,
            settings=get_settings(),
            secret_header=TEST_SECRET,
            body=WebhookTriggerIn(shape="generic", name="from-webhook"),
        )
        assert out.task_id > 0
        assert out.session_id > 0
        assert out.runner == "webhook"
        assert out.shape == "generic"

        task = db.get(Task, out.task_id)
        assert task is not None
        assert task.name == "from-webhook"
        assert task.status == "todo"
        assert task.assignee_agent_id is not None

        stub = db.get(AgentSession, out.session_id)
        assert stub is not None
        assert stub.task_id == task.id
        assert stub.runner == "webhook"
        assert stub.status == "queued"
        assert stub.summary and "webhook" in stub.summary.lower()
    finally:
        db.close()
        engine.dispose()
        get_settings.cache_clear()


def test_support_inbound_shape_assigns_support_agent(monkeypatch):
    _set_secret(monkeypatch)
    db, engine = _memory_db()
    try:
        out = handle_webhook_trigger(
            db,
            settings=get_settings(),
            secret_header=TEST_SECRET,
            body=WebhookTriggerIn(shape="support-inbound"),
        )
        assert out.shape == "support-inbound"
        assert out.agent_name == "support"
        task = db.get(Task, out.task_id)
        assert task is not None
        assert task.name == "support-inbound"
        agent = db.get(Agent, task.assignee_agent_id)
        assert agent is not None
        assert agent.name == "support"
    finally:
        db.close()
        engine.dispose()
        get_settings.cache_clear()


def test_http_valid_secret_201(monkeypatch):
    _set_secret(monkeypatch)
    db, engine = _memory_db()

    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            resp = client.post(
                "/api/v1/triggers/webhook",
                headers={"X-Webhook-Secret": TEST_SECRET},
                json={"shape": "generic", "name": "http-ok", "payload": {"src": "test"}},
            )
            assert resp.status_code == 201, resp.text
            body = resp.json()
            assert body["task_id"] > 0
            assert body["session_id"] > 0
            assert body["runner"] == "webhook"
            assert body["shape"] == "generic"

            task = db.get(Task, body["task_id"])
            assert task is not None
            assert task.name == "http-ok"
            assert "payload" in (task.description or "")
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()
        get_settings.cache_clear()


def test_http_bad_secret_401(monkeypatch):
    _set_secret(monkeypatch)
    db, engine = _memory_db()

    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            bad = client.post(
                "/api/v1/triggers/webhook",
                headers={"X-Webhook-Secret": "nope"},
                json={"shape": "generic"},
            )
            assert bad.status_code == 401, bad.text

            missing = client.post(
                "/api/v1/triggers/webhook",
                json={"shape": "generic"},
            )
            assert missing.status_code == 401, missing.text

            # No task created on auth failure
            tasks = list(db.scalars(select(Task)).all())
            assert tasks == []
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()
        get_settings.cache_clear()
