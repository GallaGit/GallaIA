"""F1.4 — Live SSE stream of thread messages (backend, mock LLM, no network)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import Base
from app.db.session import get_db
from app.main import app
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


def _teardown(db):
    app.dependency_overrides.clear()
    if hasattr(app.state, "session_factory"):
        delattr(app.state, "session_factory")
    db.close()


def _new_thread_with_user_text(client, text="Construye la feature X"):
    thread_id = client.post(
        "/api/v1/threads", json={"title": "Hilo F1.4", "created_by": "user"}
    ).json()["id"]
    r = client.post(
        f"/api/v1/threads/{thread_id}/messages",
        json={"sender": "user", "recipient": "orquestador", "kind": "text", "body": text},
    )
    assert r.status_code == 201, r.text
    return thread_id


def _parse_sse(text: str) -> list[tuple[str, str]]:
    """Split an SSE payload into (event, data) frames."""
    frames: list[tuple[str, str]] = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        name, data = None, None
        for line in block.splitlines():
            if line.startswith("event:"):
                name = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data = line[len("data:") :].strip()
        if name is not None:
            frames.append((name, data or ""))
    return frames


def test_stream_emits_plan_delegations_results_and_summary():
    db, _engine, Session = _memory_db()
    client = _client(db, Session)
    try:
        thread_id = _new_thread_with_user_text(client)
        r = client.get(f"/api/v1/threads/{thread_id}/stream")
        assert r.status_code == 200, r.text
        assert "text/event-stream" in r.headers.get("content-type", "")

        frames = _parse_sse(r.text)
        events = [name for name, _ in frames]
        assert "message" in events
        assert "heartbeat" in events
        assert events[-1] == "end"

        messages = [json.loads(data) for name, data in frames if name == "message"]
        # Replay of the user text + live advance output (mock LLM, no API key).
        assert messages[0]["sender"] == "user"
        assert messages[0]["body"] == "Construye la feature X"

        live = messages[1:]
        assert len(live) >= 1
        assert {m["sender"] for m in live} <= {"orquestador", "fe", "be"}
        assert "delegation" in {m["kind"] for m in live}
        assert "result" in {m["kind"] for m in live}
        summaries = [
            m for m in live if m["sender"] == "orquestador" and m["recipient"] == "user"
        ]
        assert len(summaries) == 1

        end_data = json.loads(frames[-1][1])
        assert end_data["reason"] == "done"
        assert end_data["created"] == len(live)
    finally:
        _teardown(db)


def test_stream_closed_thread_returns_409():
    db, _engine, Session = _memory_db()
    client = _client(db, Session)
    try:
        thread_id = _new_thread_with_user_text(client)
        assert client.patch(
            f"/api/v1/threads/{thread_id}", json={"status": "closed"}
        ).status_code == 200
        r = client.get(f"/api/v1/threads/{thread_id}/stream")
        assert r.status_code == 409, r.text
    finally:
        _teardown(db)


def test_stream_missing_thread_returns_404():
    db, _engine, Session = _memory_db()
    client = _client(db, Session)
    try:
        r = client.get("/api/v1/threads/999999/stream")
        assert r.status_code == 404, r.text
    finally:
        _teardown(db)
