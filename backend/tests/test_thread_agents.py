"""F1.2 — Agents reply inside threads (backend, injected fake LLM, no network)."""

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
from app.models import Thread
from app.services.seed import ensure_seed_agents_and_grants, seed_if_empty
from app.services.thread_agents import advance_thread


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
    payload = {"title": "Hilo F1.2", "created_by": "user"}
    payload.update(overrides)
    return client.post("/api/v1/threads", json=payload)


def _seed_thread_with_user_text(client, text="Construye la feature X"):
    thread_id = _new_thread(client).json()["id"]
    r = client.post(
        f"/api/v1/threads/{thread_id}/messages",
        json={"sender": "user", "recipient": "orquestador", "kind": "text", "body": text},
    )
    assert r.status_code == 201, r.text
    return thread_id


def _fake_llm(system: str, user: str) -> str:
    low = system.lower()
    if "\u2014 orquestador" in low:
        return json.dumps(
            {
                "plan": "Plan: repartir FE y BE.",
                "delegations": [
                    {"to": "fe", "brief": f"FE brief: {user}"},
                    {"to": "be", "brief": f"BE brief: {user}"},
                ],
            }
        )
    if "\u2014 fe" in low:
        return f"[fe] result: {user}"
    if "\u2014 be" in low:
        return f"[be] result: {user}"
    return "(unknown)"


def _bad_json_llm(system: str, user: str) -> str:
    low = system.lower()
    if "\u2014 orquestador" in low:
        return "esto no es json {{{"
    return _fake_llm(system, user)


def test_full_flow_user_to_orquestador_results_and_summary():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        thread_id = _seed_thread_with_user_text(client)
        thread = db.get(Thread, thread_id)

        created = advance_thread(db, thread, max_steps=6, llm=_fake_llm)

        assert [m.sender for m in created] == [
            "orquestador",
            "orquestador",
            "orquestador",
            "fe",
            "be",
            "orquestador",
        ]
        assert [m.kind for m in created] == [
            "text",
            "delegation",
            "delegation",
            "result",
            "result",
            "text",
        ]
        delegations = [m for m in created if m.kind == "delegation"]
        assert {d.recipient for d in delegations} == {"fe", "be"}

        summary = created[-1]
        assert summary.recipient == "user"
        assert summary.kind == "text"

        # Second advance must not duplicate anything.
        again = advance_thread(db, thread, max_steps=6, llm=_fake_llm)
        assert again == []

        detail = client.get(f"/api/v1/threads/{thread_id}").json()
        assert len(detail["messages"]) == 7  # user + 6 replies
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_invalid_json_falls_back_to_both_agents():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        user_text = "Arregla el bug del login"
        thread_id = _seed_thread_with_user_text(client, text=user_text)
        thread = db.get(Thread, thread_id)

        created = advance_thread(db, thread, max_steps=1, llm=_bad_json_llm)

        delegations = [m for m in created if m.kind == "delegation"]
        assert {d.recipient for d in delegations} == {"fe", "be"}
        assert all(d.body == user_text for d in delegations)
        assert any(m.kind == "text" and m.sender == "orquestador" for m in created)
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_max_steps_caps_replies_per_call():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        thread_id = _new_thread(client).json()["id"]
        for recipient in ("fe", "be"):
            r = client.post(
                f"/api/v1/threads/{thread_id}/messages",
                json={
                    "sender": "user",
                    "recipient": recipient,
                    "kind": "delegation",
                    "body": f"trabaja {recipient}",
                },
            )
            assert r.status_code == 201, r.text
        thread = db.get(Thread, thread_id)

        first = advance_thread(db, thread, max_steps=1, llm=_fake_llm)
        assert len(first) == 1
        assert first[0].kind == "result"

        second = advance_thread(db, thread, max_steps=1, llm=_fake_llm)
        assert len(second) == 1
        assert second[0].kind == "result"
        assert second[0].sender != first[0].sender

        # No orquestador delegation exists, so nothing left to answer.
        assert advance_thread(db, thread, max_steps=6, llm=_fake_llm) == []
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_default_mock_used_without_openrouter_key(monkeypatch):
    monkeypatch.setattr(
        "app.providers.openrouter.openrouter_api_key", lambda: "", raising=True
    )
    db, _engine = _memory_db()
    client = _client(db)
    try:
        thread_id = _seed_thread_with_user_text(client, text="Haz una demo")
        thread = db.get(Thread, thread_id)

        created = advance_thread(db, thread, max_steps=6, llm=None)

        results = {m.sender: m.body for m in created if m.kind == "result"}
        assert results["fe"].startswith("[fe] mock result:")
        assert results["be"].startswith("[be] mock result:")
        assert any(m.kind == "text" and m.recipient == "user" for m in created)
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_advance_route_returns_created_messages():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        thread_id = _seed_thread_with_user_text(client)
        r = client.post(f"/api/v1/threads/{thread_id}/advance")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "created" in body
        assert len(body["created"]) >= 1
        assert {m["sender"] for m in body["created"]} <= {"orquestador", "fe", "be"}

        # max_steps bounds are validated by FastAPI.
        assert client.post(
            f"/api/v1/threads/{thread_id}/advance", params={"max_steps": 0}
        ).status_code == 422
        assert client.post(
            f"/api/v1/threads/{thread_id}/advance", params={"max_steps": 21}
        ).status_code == 422
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_advance_missing_thread_404_and_closed_thread_409():
    db, _engine = _memory_db()
    client = _client(db)
    try:
        assert client.post("/api/v1/threads/999/advance").status_code == 404

        thread_id = _new_thread(client).json()["id"]
        assert client.patch(
            f"/api/v1/threads/{thread_id}", json={"status": "closed"}
        ).status_code == 200
        closed = client.post(f"/api/v1/threads/{thread_id}/advance")
        assert closed.status_code == 409, closed.text
    finally:
        app.dependency_overrides.clear()
        db.close()
