"""Phase 7 slice 2: Inbox list / reply / resolve decisions API."""

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
from app.models import InboxMessage
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


def _seed_open_message(db, *, body: str = "Need human decision") -> InboxMessage:
    msg = InboxMessage(
        from_role="agent",
        agent_id=None,
        session_id=None,
        task_id=None,
        kind="text",
        body=body,
        status="open",
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def test_list_inbox_and_filter_open():
    db, _engine = _memory_db()
    try:
        open_msg = _seed_open_message(db, body="open one")
        answered = InboxMessage(
            from_role="agent",
            kind="text",
            body="already done",
            status="answered",
            reply_body="ok",
        )
        db.add(answered)
        db.commit()

        client = _client(db)
        all_items = client.get("/api/v1/inbox").json()
        assert len(all_items) >= 2
        ids = {m["id"] for m in all_items}
        assert open_msg.id in ids

        open_only = client.get("/api/v1/inbox", params={"status": "open"}).json()
        assert all(m["status"] == "open" for m in open_only)
        assert any(m["id"] == open_msg.id for m in open_only)
    finally:
        db.close()
        app.dependency_overrides.clear()


def test_reply_closes_message_and_emits_activity():
    db, _engine = _memory_db()
    try:
        msg = _seed_open_message(db)
        client = _client(db)

        res = client.post(
            f"/api/v1/inbox/{msg.id}/reply",
            json={"body": "Approved — continue"},
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["status"] == "answered"
        assert data["reply_body"] == "Approved — continue"
        assert data["answered_at"] is not None

        got = client.get(f"/api/v1/inbox/{msg.id}").json()
        assert got["status"] == "answered"

        # second reply rejected
        again = client.post(
            f"/api/v1/inbox/{msg.id}/reply",
            json={"body": "again"},
        )
        assert again.status_code == 400

        events = list(
            db.scalars(
                select(ActivityEvent)
                .where(ActivityEvent.type == "inbox.replied")
                .order_by(ActivityEvent.id.desc())
            ).all()
        )
        assert len(events) >= 1
        assert f"Inbox #{msg.id}" in events[0].message
    finally:
        db.close()
        app.dependency_overrides.clear()


def test_resolve_closes_with_optional_note():
    db, _engine = _memory_db()
    try:
        msg = _seed_open_message(db, body="resolve me")
        client = _client(db)

        res = client.post(
            f"/api/v1/inbox/{msg.id}/resolve",
            json={"note": "Ack"},
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["status"] == "answered"
        assert data["reply_body"] == "Ack"

        events = list(
            db.scalars(
                select(ActivityEvent).where(ActivityEvent.type == "inbox.resolved")
            ).all()
        )
        assert len(events) >= 1
    finally:
        db.close()
        app.dependency_overrides.clear()


def test_reply_not_found():
    db, _engine = _memory_db()
    try:
        client = _client(db)
        res = client.post("/api/v1/inbox/999999/reply", json={"body": "nope"})
        assert res.status_code == 404
    finally:
        db.close()
        app.dependency_overrides.clear()
