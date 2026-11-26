"""Fase B — control-plane inbox approvals (F2.2c) + SSE fan-out + auth."""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

import pytest

pytest.importorskip("langgraph")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import ActivityEvent, InboxMessage, Thread  # noqa: E402
from app.runtime import thread_graph  # noqa: E402
from app.services.seed import ensure_seed_agents_and_grants, seed_if_empty  # noqa: E402
from app.services.thread_agents import advance_thread  # noqa: E402

TEST_OPERATOR_TOKEN = "test-operator-token-0123456789abcdefghijklmnopqrstuv"


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


def _fake_llm(system: str, user: str) -> str:
    low = system.lower()
    if "— orquestador" in low:
        return json.dumps(
            {
                "plan": "Plan: repartir FE y BE.",
                "delegations": [
                    {"to": "fe", "brief": f"FE brief: {user}"},
                    {"to": "be", "brief": f"BE brief: {user}"},
                ],
            }
        )
    if "— fe" in low:
        return f"[fe] result: {user}"
    if "— be" in low:
        return f"[be] result: {user}"
    return "(unknown)"


def _new_thread(client, text="Construye la feature X"):
    thread_id = client.post(
        "/api/v1/threads", json={"title": "Hilo fase B", "created_by": "user"}
    ).json()["id"]
    r = client.post(
        f"/api/v1/threads/{thread_id}/messages",
        json={
            "sender": "user",
            "recipient": "orquestador",
            "kind": "text",
            "body": text,
        },
    )
    assert r.status_code == 201, r.text
    return thread_id


def _open_approvals(db):
    return list(
        db.scalars(
            select(InboxMessage)
            .where(
                InboxMessage.kind == "thread_approval",
                InboxMessage.status == "open",
            )
            .order_by(InboxMessage.id)
        ).all()
    )


def _decide(client, inbox_id: int, approved: bool, note: str | None = None):
    return client.post(
        f"/api/v1/inbox/{inbox_id}/decide",
        json={"approved": approved, "note": note},
    )


@pytest.fixture(autouse=True)
def _runtime(monkeypatch):
    monkeypatch.setenv("GALLAIA_THREAD_ENGINE", "langgraph")
    monkeypatch.setenv("GALLAIA_THREAD_APPROVAL", "true")
    monkeypatch.setenv("GALLAIA_CHECKPOINT_DB", "memory")
    get_settings.cache_clear()
    thread_graph.reset_runtime()
    yield
    thread_graph.reset_runtime()
    get_settings.cache_clear()
    app.dependency_overrides.clear()


def test_creation_lists_open_approval_with_target_agent():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        thread_id = _new_thread(client)
        advance_thread(db, db.get(Thread, thread_id), max_steps=6, llm=_fake_llm)

        approvals = _open_approvals(db)
        assert len(approvals) == 1

        listed = client.get("/api/v1/inbox", params={"status": "open"}).json()
        assert len(listed) >= 1
        row = next(i for i in listed if i["id"] == approvals[0].id)
        assert row["kind"] == "thread_approval"
        assert row["status"] == "open"
        assert row["thread_id"] == thread_id
        assert row["target_agent"] in {"fe", "be"}

        pending_events = list(
            db.scalars(
                select(ActivityEvent).where(
                    ActivityEvent.type == "inbox.approval_pending"
                )
            ).all()
        )
        assert pending_events
        assert f"Inbox #{approvals[0].id}" in pending_events[0].message
    finally:
        db.close()


def test_approve_closes_and_resumes():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        thread_id = _new_thread(client)
        advance_thread(db, db.get(Thread, thread_id), max_steps=6, llm=_fake_llm)
        inbox_id = _open_approvals(db)[0].id

        res = _decide(client, inbox_id, True)
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["inbox"]["status"] == "answered"
        assert body["inbox"]["id"] == inbox_id

        decided = list(
            db.scalars(
                select(ActivityEvent).where(ActivityEvent.type == "inbox.decided")
            ).all()
        )
        assert decided
        assert "approved" in decided[-1].message
    finally:
        db.close()


def test_reject_persists_note_and_result():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        thread_id = _new_thread(client)
        advance_thread(db, db.get(Thread, thread_id), max_steps=6, llm=_fake_llm)
        approval = _open_approvals(db)[0]

        res = _decide(client, approval.id, False, note="no por ahora")
        assert res.status_code == 200, res.text
        assert res.json()["inbox"]["status"] == "answered"
        assert res.json()["inbox"]["reply_body"] == "no por ahora"
        rejected = [
            m
            for m in res.json()["created"]
            if m["kind"] == "result" and "[rechazado por el humano]" in m["body"]
        ]
        assert rejected
        assert "no por ahora" in rejected[0]["body"]
    finally:
        db.close()


def test_duplicate_decide_and_missing_id():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        thread_id = _new_thread(client)
        advance_thread(db, db.get(Thread, thread_id), max_steps=6, llm=_fake_llm)
        inbox_id = _open_approvals(db)[0].id

        assert _decide(client, inbox_id, True).status_code == 200
        dup = _decide(client, inbox_id, True)
        assert dup.status_code == 400

        missing = _decide(client, 999999, True)
        assert missing.status_code == 404
    finally:
        db.close()


def test_operator_token_required_for_inbox_and_decide():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        thread_id = _new_thread(client)
        advance_thread(db, db.get(Thread, thread_id), max_steps=6, llm=_fake_llm)
        inbox_id = _open_approvals(db)[0].id

        def _override():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_db] = _override

        no_auth = TestClient(app, raise_server_exceptions=False)
        no_auth.headers.pop("Authorization", None)
        assert no_auth.get("/api/v1/inbox").status_code == 401

        wrong = TestClient(
            app,
            raise_server_exceptions=False,
            headers={
                "Authorization": (
                    "Bearer wrong-token-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                )
            },
        )
        assert wrong.get("/api/v1/inbox").status_code == 401
        assert (
            wrong.post(
                f"/api/v1/inbox/{inbox_id}/decide",
                json={"approved": True},
            ).status_code
            == 401
        )

        ok = client.get("/api/v1/inbox")
        assert ok.status_code == 200
        assert _decide(client, inbox_id, True).status_code == 200
    finally:
        db.close()


def test_sse_emits_inbox_on_create_and_decide():
    """Activity stream carries `event: inbox` when an approval is created/decided."""
    db, _engine = _memory_db()
    client = _client(db)
    texts: list[str] = []

    def _advance_later():
        time.sleep(0.1)
        thread_id = _new_thread(client)
        advance_thread(db, db.get(Thread, thread_id), max_steps=6, llm=_fake_llm)
        approvals = _open_approvals(db)
        assert approvals
        time.sleep(0.05)
        assert _decide(client, approvals[0].id, True).status_code == 200

    try:
        t = threading.Thread(target=_advance_later, daemon=True)
        t.start()
        with client.stream(
            "GET",
            "/api/v1/activity/stream",
            params={"heartbeat_seconds": 0.2, "max_seconds": 2.5},
        ) as resp:
            assert resp.status_code == 200
            text = "".join(resp.iter_text())
            texts.append(text)
        t.join(timeout=5)
        joined = "\n".join(texts)
        assert "event: inbox" in joined
        assert '"action": "pending"' in joined or '"action":"pending"' in joined
        assert '"action": "decided"' in joined or '"action":"decided"' in joined
        assert "event: activity" in joined
        assert "inbox.approval_pending" in joined or "inbox.decided" in joined
    finally:
        db.close()
