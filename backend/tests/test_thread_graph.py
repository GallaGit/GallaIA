"""F2.2a — Optional LangGraph engine produces the same messages (no network).

The LangGraph tests skip when the package is missing; the fallback tests
(engine selected but langgraph unavailable / unknown engine) always run.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Thread
from app.runtime import thread_graph
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


def _new_thread_with_user_text(client, text="Construye la feature X"):
    thread_id = client.post(
        "/api/v1/threads", json={"title": "Hilo F2.2a", "created_by": "user"}
    ).json()["id"]
    payload = {
        "sender": "user",
        "recipient": "orquestador",
        "kind": "text",
        "body": text,
    }
    r = client.post(f"/api/v1/threads/{thread_id}/messages", json=payload)
    assert r.status_code == 201, r.text
    return thread_id


def _new_thread_with_delegations(client):
    thread_id = client.post(
        "/api/v1/threads", json={"title": "Hilo F2.2a", "created_by": "user"}
    ).json()["id"]
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
    return thread_id


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


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    """Never leak the selected engine into other test modules."""
    yield
    get_settings.cache_clear()


@pytest.fixture
def require_langgraph():
    pytest.importorskip("langgraph.graph")


def _select_engine(monkeypatch, engine: str) -> None:
    monkeypatch.setenv("GALLAIA_THREAD_ENGINE", engine)
    get_settings.cache_clear()


def _shape(messages):
    return [(m.sender, m.recipient, m.kind, m.body) for m in messages]


def test_langgraph_engine_matches_classic(monkeypatch, require_langgraph):
    db, _engine = _memory_db()
    client = _client(db)
    try:
        _select_engine(monkeypatch, "classic")
        classic_thread = _new_thread_with_user_text(client)
        classic = advance_thread(
            db, db.get(Thread, classic_thread), max_steps=6, llm=_fake_llm
        )

        _select_engine(monkeypatch, "langgraph")
        graph_thread = _new_thread_with_user_text(client)
        graphed = advance_thread(
            db, db.get(Thread, graph_thread), max_steps=6, llm=_fake_llm
        )

        assert _shape(graphed) == _shape(classic)
        assert len(graphed) == 6
        assert [m.sender for m in graphed] == [
            "orquestador",
            "orquestador",
            "orquestador",
            "fe",
            "be",
            "orquestador",
        ]
        # Same activity events: 6 replies per engine + the 2 user messages.
        events = client.get("/api/v1/activity?limit=50").json()
        assert len([e for e in events if e["type"] == "message.created"]) == 14
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_langgraph_max_steps_caps_and_continues(monkeypatch, require_langgraph):
    db, _engine = _memory_db()
    client = _client(db)
    try:
        _select_engine(monkeypatch, "langgraph")
        thread_id = _new_thread_with_delegations(client)
        thread = db.get(Thread, thread_id)

        first = advance_thread(db, thread, max_steps=1, llm=_fake_llm)
        assert len(first) == 1
        assert first[0].kind == "result"

        second = advance_thread(db, thread, max_steps=1, llm=_fake_llm)
        assert len(second) == 1
        assert second[0].kind == "result"
        assert second[0].id != first[0].id
        assert second[0].sender != first[0].sender

        assert advance_thread(db, thread, max_steps=6, llm=_fake_llm) == []
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_get_thread_graph_state_holds_created_ids(monkeypatch, require_langgraph):
    db, _engine = _memory_db()
    client = _client(db)
    try:
        _select_engine(monkeypatch, "langgraph")
        thread_id = _new_thread_with_user_text(client)
        thread = db.get(Thread, thread_id)

        created = advance_thread(db, thread, max_steps=6, llm=_fake_llm)

        state = thread_graph.get_thread_graph_state(thread_id)
        assert state is not None
        assert state["created"] == [m.id for m in created]
        assert state["steps"] == 4
        assert state["thread_id"] == thread_id
        assert thread_graph.get_thread_graph_state(987654) is None
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_langgraph_engine_without_package_falls_back(monkeypatch):
    monkeypatch.setattr(thread_graph, "langgraph_available", lambda: False)
    db, _engine = _memory_db()
    client = _client(db)
    try:
        _select_engine(monkeypatch, "classic")
        classic_thread = _new_thread_with_user_text(client)
        classic = advance_thread(
            db, db.get(Thread, classic_thread), max_steps=6, llm=_fake_llm
        )

        _select_engine(monkeypatch, "langgraph")
        fallback_thread = _new_thread_with_user_text(client)
        fallback = advance_thread(
            db, db.get(Thread, fallback_thread), max_steps=6, llm=_fake_llm
        )

        assert _shape(fallback) == _shape(classic)
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_unknown_engine_value_uses_classic(monkeypatch):
    db, _engine = _memory_db()
    client = _client(db)
    try:
        _select_engine(monkeypatch, "quantum")
        assert thread_graph.thread_engine() == "classic"

        thread_id = _new_thread_with_user_text(client)
        created = advance_thread(
            db, db.get(Thread, thread_id), max_steps=6, llm=_fake_llm
        )
        assert [m.sender for m in created] == [
            "orquestador",
            "orquestador",
            "orquestador",
            "fe",
            "be",
            "orquestador",
        ]
    finally:
        app.dependency_overrides.clear()
        db.close()