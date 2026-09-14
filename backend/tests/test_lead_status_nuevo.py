"""Phase 5 slice 3: lead-status-nuevo -> instantiate lead-intake-workflow."""

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
from app.main import app
from app.models import Task
from app.schemas.trigger import LeadStatusNuevoIn
from app.services.seed import ensure_seed_agents_and_grants, seed_if_empty
from app.services.templates import LEAD_INTAKE_SLUG
from app.services.triggers import handle_lead_status_nuevo

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
                "/api/v1/triggers/lead-status-nuevo",
                headers={"X-Webhook-Secret": "nope"},
                json={"leadId": "42"},
            )
            assert bad.status_code == 401, bad.text

            missing = client.post(
                "/api/v1/triggers/lead-status-nuevo",
                json={"leadId": "42"},
            )
            assert missing.status_code == 401, missing.text

            tasks = list(db.scalars(select(Task)).all())
            assert tasks == []
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()
        get_settings.cache_clear()


def test_http_missing_lead_id_400(monkeypatch):
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
            empty = client.post(
                "/api/v1/triggers/lead-status-nuevo",
                headers={"X-Webhook-Secret": TEST_SECRET},
                json={},
            )
            assert empty.status_code == 400, empty.text

            blank = client.post(
                "/api/v1/triggers/lead-status-nuevo",
                headers={"X-Webhook-Secret": TEST_SECRET},
                json={"leadId": "  "},
            )
            assert blank.status_code == 400, blank.text

            tasks = list(db.scalars(select(Task)).all())
            assert tasks == []
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()
        get_settings.cache_clear()


def test_http_valid_creates_two_tasks_200(monkeypatch):
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
                "/api/v1/triggers/lead-status-nuevo",
                headers={"X-Webhook-Secret": TEST_SECRET},
                json={"leadId": "42"},
            )
            assert resp.status_code == 200, resp.text
            body = resp.json()
            assert body["lead_id"] == "42"
            assert body["template_slug"] == LEAD_INTAKE_SLUG
            assert body["task_count"] == 2
            assert len(body["task_ids"]) == 2
            assert body["run_id"]

            tasks = [db.get(Task, tid) for tid in body["task_ids"]]
            assert all(t is not None for t in tasks)
            assert tasks[0].step_index == 1
            assert tasks[1].step_index == 2
            assert tasks[1].depends_on_task_id == tasks[0].id
            assert tasks[0].template_run_id == tasks[1].template_run_id == body["run_id"]
            assert "42" in tasks[0].name
            assert "42" in tasks[1].name
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()
        get_settings.cache_clear()


def test_service_instantiates_lead_intake(monkeypatch):
    _set_secret(monkeypatch)
    db, engine = _memory_db()
    try:
        out = handle_lead_status_nuevo(
            db,
            settings=get_settings(),
            secret_header=TEST_SECRET,
            body=LeadStatusNuevoIn(leadId=99),
        )
        assert out.lead_id == "99"
        assert out.task_count == 2
        assert out.template_slug == LEAD_INTAKE_SLUG
    finally:
        db.close()
        engine.dispose()
        get_settings.cache_clear()
