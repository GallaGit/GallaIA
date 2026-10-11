"""F1.1 — Threads and agent-to-agent messages (backend)."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.activity import ActivityEvent
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


def _client(db):
    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    return TestClient(app)


def _new_thread(client, **overrides):
    payload = {"title": "Hilo de prueba", "created_by": "user"}
    payload.update(overrides)
    return client.post("/api/v1/threads", json=payload)


def test_create_and_list_threads():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        r = _new_thread(client, title="Sprint F1")
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["title"] == "Sprint F1"
        assert body["created_by"] == "user"
        assert body["status"] == "open"
        assert body["id"] > 0

        listed = client.get("/api/v1/threads")
        assert listed.status_code == 200
        assert [t["id"] for t in listed.json()] == [body["id"]]

        filtered = client.get("/api/v1/threads", params={"status": "closed"})
        assert filtered.status_code == 200
        assert filtered.json() == []
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_create_thread_with_agent_and_project():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        r = _new_thread(client, title="Agente", created_by="orquestador")
        assert r.status_code == 201, r.text
        assert r.json()["created_by"] == "orquestador"

        missing = _new_thread(client, title="x", project_id=9999)
        assert missing.status_code == 404
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_create_thread_rejects_unknown_creator():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        r = _new_thread(client, created_by="ghost")
        assert r.status_code == 422, r.text
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_get_thread_messages_ordered_by_created_at():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        thread_id = _new_thread(client).json()["id"]
        for sender, recipient, kind in (
            ("user", "orquestador", "text"),
            ("orquestador", "fe", "delegation"),
            ("fe", "orquestador", "result"),
        ):
            payload = {"sender": sender, "kind": kind, "body": f"from {sender}"}
            if recipient is not None:
                payload["recipient"] = recipient
            r = client.post(f"/api/v1/threads/{thread_id}/messages", json=payload)
            assert r.status_code == 201, r.text

        detail = client.get(f"/api/v1/threads/{thread_id}")
        assert detail.status_code == 200
        body = detail.json()
        assert [m["sender"] for m in body["messages"]] == [
            "user",
            "orquestador",
            "fe",
        ]
        assert [m["kind"] for m in body["messages"]] == [
            "text",
            "delegation",
            "result",
        ]
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_message_broadcast_and_activity_event():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        thread_id = _new_thread(client).json()["id"]
        r = client.post(
            f"/api/v1/threads/{thread_id}/messages",
            json={"sender": "orquestador", "body": "hola a todos"},
        )
        assert r.status_code == 201, r.text
        assert r.json()["recipient"] is None

        rows = list(
            db.scalars(
                select(ActivityEvent).where(ActivityEvent.type == "message.created")
            ).all()
        )
        assert len(rows) == 1
        assert f"thread {thread_id}" in rows[0].message
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_message_rejects_unknown_sender_and_recipient():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        thread_id = _new_thread(client).json()["id"]

        bad_sender = client.post(
            f"/api/v1/threads/{thread_id}/messages",
            json={"sender": "ghost", "body": "hola"},
        )
        assert bad_sender.status_code == 422, bad_sender.text

        bad_recipient = client.post(
            f"/api/v1/threads/{thread_id}/messages",
            json={"sender": "user", "recipient": "ghost", "body": "hola"},
        )
        assert bad_recipient.status_code == 422, bad_recipient.text
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_delegation_only_from_orquestador_or_user():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        thread_id = _new_thread(client).json()["id"]

        denied = client.post(
            f"/api/v1/threads/{thread_id}/messages",
            json={
                "sender": "fe",
                "recipient": "be",
                "kind": "delegation",
                "body": "haz esto",
            },
        )
        assert denied.status_code == 422, denied.text

        for sender in ("orquestador", "user"):
            ok = client.post(
                f"/api/v1/threads/{thread_id}/messages",
                json={
                    "sender": sender,
                    "recipient": "be",
                    "kind": "delegation",
                    "body": "haz esto",
                },
            )
            assert ok.status_code == 201, ok.text
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_missing_thread_returns_404():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        assert client.get("/api/v1/threads/999").status_code == 404
        assert client.patch(
            "/api/v1/threads/999", json={"status": "closed"}
        ).status_code == 404
        assert client.post(
            "/api/v1/threads/999/messages",
            json={"sender": "user", "body": "hola"},
        ).status_code == 404
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_close_thread_and_reject_messages():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        thread_id = _new_thread(client).json()["id"]
        closed = client.patch(
            f"/api/v1/threads/{thread_id}", json={"status": "closed"}
        )
        assert closed.status_code == 200, closed.text
        assert closed.json()["status"] == "closed"

        blocked = client.post(
            f"/api/v1/threads/{thread_id}/messages",
            json={"sender": "user", "body": "tarde"},
        )
        assert blocked.status_code == 409, blocked.text
    finally:
        app.dependency_overrides.clear()
        db.close()
