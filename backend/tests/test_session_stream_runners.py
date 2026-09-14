"""Phase 7 slice 3: session live SSE + local runner routing stub."""

from __future__ import annotations

import sys
import threading
import time
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
from app.models import Agent, AgentSession
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
    return db, engine, Session


def _client(db, Session):
    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    app.state.session_factory = Session
    return TestClient(app)


def _make_session(db, *, status="running", runner="mock", tools=None) -> AgentSession:
    agent = db.scalars(select(Agent).limit(1)).first()
    assert agent is not None
    row = AgentSession(
        agent_id=agent.id,
        task_id=None,
        runner=runner,
        status=status,
    )
    if tools:
        row.set_tool_events(tools)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_session_stream_replay_heartbeat_end():
    db, _engine, Session = _memory_db()
    client = _client(db, Session)
    try:
        row = _make_session(
            db,
            tools=[
                {"name": "echo", "input": {}, "output": {"ok": True}, "at": "t1"},
                {"name": "fs.read", "input": {"path": "a"}, "output": {"n": 1}, "at": "t2"},
            ],
        )
        with client.stream(
            "GET",
            f"/api/v1/sessions/{row.id}/stream",
            params={"heartbeat_seconds": 0.1, "max_seconds": 0.35, "poll_seconds": 0.1},
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")
            text = "".join(resp.iter_text())
        assert "event: status" in text
        assert '"status": "running"' in text or '"status":"running"' in text
        assert "event: tool" in text
        assert "echo" in text
        assert "fs.read" in text
        assert "event: heartbeat" in text
        assert "event: end" in text
        assert "max_seconds" in text
    finally:
        app.dependency_overrides.clear()
        if hasattr(app.state, "session_factory"):
            delattr(app.state, "session_factory")
        db.close()


def test_session_stream_not_found():
    db, _engine, Session = _memory_db()
    client = _client(db, Session)
    try:
        with client.stream(
            "GET",
            "/api/v1/sessions/999999/stream",
            params={"max_seconds": 0.2, "heartbeat_seconds": 0.1},
        ) as resp:
            text = "".join(resp.iter_text())
        assert "event: error" in text
        assert "event: end" in text
        assert "not_found" in text
    finally:
        app.dependency_overrides.clear()
        if hasattr(app.state, "session_factory"):
            delattr(app.state, "session_factory")
        db.close()


def test_session_stream_sees_live_tool_append():
    db, _engine, Session = _memory_db()
    client = _client(db, Session)
    row = _make_session(db, tools=[{"name": "start", "input": {}, "output": {}, "at": "t0"}])
    appended = {"ok": False}

    def _append_later():
        time.sleep(0.1)
        # Use a separate session on the same engine so the stream poll sees it
        with Session() as s:
            live = s.get(AgentSession, row.id)
            assert live is not None
            events = live.get_tool_events()
            events.append(
                {"name": "live.tool", "input": {}, "output": {"x": 1}, "at": "t1"}
            )
            live.set_tool_events(events)
            live.status = "completed"
            s.add(live)
            s.commit()
            appended["ok"] = True

    try:
        t = threading.Thread(target=_append_later, daemon=True)
        t.start()
        with client.stream(
            "GET",
            f"/api/v1/sessions/{row.id}/stream",
            params={"heartbeat_seconds": 0.5, "max_seconds": 0.7, "poll_seconds": 0.08},
        ) as resp:
            text = "".join(resp.iter_text())
        t.join(timeout=2)
        assert appended["ok"]
        assert "live.tool" in text
        assert "completed" in text
    finally:
        app.dependency_overrides.clear()
        if hasattr(app.state, "session_factory"):
            delattr(app.state, "session_factory")
        db.close()


def test_runner_route_mock_and_local_stub(monkeypatch):
    monkeypatch.setenv("GALLAIA_RUNNER_ROUTE", "mock")
    get_settings.cache_clear()
    db, _engine, Session = _memory_db()
    client = _client(db, Session)
    try:
        info = client.get("/api/v1/runners/route")
        assert info.status_code == 200, info.text
        body = info.json()
        assert body["configured_route"] == "mock"
        assert body["effective_runner"] == "mock"
        assert body["local_runner_available"] is False

        row = _make_session(db)
        r = client.post(
            "/api/v1/runners/route",
            json={"route": "local", "session_id": row.id},
        )
        assert r.status_code == 200, r.text
        out = r.json()
        assert out["intended"] == "local"
        assert out["effective_runner"] == "local-stub"
        assert out["status"] == "recorded"
        assert out["local_runner_available"] is False
        assert "not implemented" in out["note"].lower() or "future" in out["note"].lower() or "local-stub" in out["note"]

        db.refresh(row)
        assert row.runner == "local-stub"

        r2 = client.post("/api/v1/runners/route", json={"route": "mock"})
        assert r2.status_code == 200
        assert r2.json()["effective_runner"] == "mock"
    finally:
        app.dependency_overrides.clear()
        if hasattr(app.state, "session_factory"):
            delattr(app.state, "session_factory")
        db.close()
        get_settings.cache_clear()


def test_runner_route_respects_settings_local(monkeypatch):
    monkeypatch.setenv("GALLAIA_RUNNER_ROUTE", "local")
    get_settings.cache_clear()
    try:
        s = get_settings()
        assert s.runner_route == "local"
        db, _engine, Session = _memory_db()
        client = _client(db, Session)
        try:
            info = client.get("/api/v1/runners/route").json()
            assert info["configured_route"] == "local"
            assert info["effective_runner"] == "local-stub"
        finally:
            app.dependency_overrides.clear()
            if hasattr(app.state, "session_factory"):
                delattr(app.state, "session_factory")
            db.close()
    finally:
        get_settings.cache_clear()


def test_runner_route_session_not_found():
    db, _engine, Session = _memory_db()
    client = _client(db, Session)
    try:
        r = client.post(
            "/api/v1/runners/route",
            json={"route": "local", "session_id": 999999},
        )
        assert r.status_code == 404
    finally:
        app.dependency_overrides.clear()
        if hasattr(app.state, "session_factory"):
            delattr(app.state, "session_factory")
        db.close()
