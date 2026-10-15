"""F1.5 — Thread delegations graph (backend)."""

from __future__ import annotations

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
    payload = {"title": "Hilo F1.5", "created_by": "user"}
    payload.update(overrides)
    return client.post("/api/v1/threads", json=payload)


def test_empty_thread_has_no_delegations():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        thread_id = _new_thread(client).json()["id"]
        r = client.get(f"/api/v1/threads/{thread_id}/delegations")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["thread_id"] == thread_id
        assert body["nodes"] == ["user", "orquestador", "fe", "be"]
        assert body["edges"] == []
        assert body["summary_id"] is None
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_advance_produces_answered_delegations_and_summary(monkeypatch):
    monkeypatch.setattr(
        "app.providers.openrouter.openrouter_api_key", lambda: "", raising=True
    )
    db, _engine = _memory_db()
    client = _client(db)
    try:
        thread_id = _new_thread(client).json()["id"]
        r = client.post(
            f"/api/v1/threads/{thread_id}/messages",
            json={
                "sender": "user",
                "recipient": "orquestador",
                "kind": "text",
                "body": "Construye la feature X",
            },
        )
        assert r.status_code == 201, r.text

        adv = client.post(
            f"/api/v1/threads/{thread_id}/advance", params={"max_steps": 6}
        )
        assert adv.status_code == 200, adv.text

        r = client.get(f"/api/v1/threads/{thread_id}/delegations")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["thread_id"] == thread_id
        assert body["nodes"] == ["user", "orquestador", "fe", "be"]
        assert len(body["edges"]) == 2
        assert {e["target"] for e in body["edges"]} == {"fe", "be"}
        assert all(e["source"] == "orquestador" for e in body["edges"])
        assert all(e["status"] == "answered" for e in body["edges"])
        assert all(e["result_id"] is not None for e in body["edges"])
        assert all(e["brief"] for e in body["edges"])
        assert body["summary_id"] is not None
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_manual_delegations_without_results_are_pending():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        thread_id = _new_thread(client).json()["id"]
        for recipient in ("fe", "be"):
            r = client.post(
                f"/api/v1/threads/{thread_id}/messages",
                json={
                    "sender": "orquestador",
                    "recipient": recipient,
                    "kind": "delegation",
                    "body": f"trabaja {recipient}",
                },
            )
            assert r.status_code == 201, r.text

        r = client.get(f"/api/v1/threads/{thread_id}/delegations")
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["edges"]) == 2
        assert {e["target"] for e in body["edges"]} == {"fe", "be"}
        assert all(e["status"] == "pending" for e in body["edges"])
        assert all(e["result_id"] is None for e in body["edges"])
        assert all(e["result_body"] is None for e in body["edges"])
        assert body["summary_id"] is None
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_delegations_missing_thread_404():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        assert client.get("/api/v1/threads/999/delegations").status_code == 404
    finally:
        app.dependency_overrides.clear()
        db.close()
