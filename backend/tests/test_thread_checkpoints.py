"""F2.2b — LangGraph checkpoints persist in SQLite (no network).

The checkpoint tests skip when `langgraph-checkpoint-sqlite` is missing; the
fallback tests (memory target / missing SqliteSaver) always run when langgraph
itself is installed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("langgraph.checkpoint.sqlite")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Message, Thread  # noqa: E402
from app.runtime import thread_graph  # noqa: E402
from app.services.seed import ensure_seed_agents_and_grants, seed_if_empty  # noqa: E402
from app.services.thread_agents import advance_thread  # noqa: E402


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
        "/api/v1/threads", json={"title": "Hilo F2.2b", "created_by": "user"}
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


def _shape(messages):
    return [(m.sender, m.recipient, m.kind, m.body) for m in messages]


@pytest.fixture(autouse=True)
def _runtime(monkeypatch, tmp_path):
    """LangGraph engine + SQLite checkpoints in a per-test file."""
    monkeypatch.setenv("GALLAIA_THREAD_ENGINE", "langgraph")
    monkeypatch.setenv("GALLAIA_CHECKPOINT_DB", str(tmp_path / "cp.db"))
    get_settings.cache_clear()
    thread_graph.reset_runtime()
    yield
    thread_graph.reset_runtime()
    get_settings.cache_clear()


@pytest.fixture
def require_langgraph():
    pytest.importorskip("langgraph.graph")


def test_sqlite_checkpointer_used_and_db_file_created(require_langgraph):
    assert thread_graph.checkpointer_kind() == "sqlite"
    db, _engine = _memory_db()
    client = _client(db)
    try:
        thread_id = _new_thread_with_user_text(client)
        created = advance_thread(db, db.get(Thread, thread_id), max_steps=6, llm=_fake_llm)
        assert len(created) == 6
        assert thread_graph.checkpointer_kind() == "sqlite"
        checkpoint_path = Path(get_settings().checkpoint_db)
        assert checkpoint_path.exists()
        assert checkpoint_path.stat().st_size > 0
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_checkpoint_survives_restart_and_continues_without_duplicates(monkeypatch):
    """A SQLite checkpoint keeps state across a simulated process restart."""
    db, _engine = _memory_db()
    client = _client(db)
    try:
        # Reference: a classic full run on a fresh thread (same messages).
        monkeypatch.setenv("GALLAIA_THREAD_ENGINE", "classic")
        get_settings.cache_clear()
        classic_thread = _new_thread_with_user_text(client)
        classic = advance_thread(
            db, db.get(Thread, classic_thread), max_steps=6, llm=_fake_llm
        )
        assert len(classic) == 6

        monkeypatch.setenv("GALLAIA_THREAD_ENGINE", "langgraph")
        get_settings.cache_clear()
        thread_graph.reset_runtime()

        thread_id = _new_thread_with_user_text(client)
        thread = db.get(Thread, thread_id)
        # Step 1 answers the user text: plan + 2 delegations (3 messages).
        first = advance_thread(db, thread, max_steps=1, llm=_fake_llm)
        assert len(first) == 3

        # Simulated restart: new checkpointer, same SQLite file.
        thread_graph.reset_runtime()
        state = thread_graph.get_thread_graph_state(thread_id)
        assert state is not None
        assert state["created"] == [m.id for m in first]

        # Continuing on the "new process" adds no duplicate replies.
        rest = advance_thread(db, thread, max_steps=6, llm=_fake_llm)
        assert rest and len(first + rest) == 6
        assert _shape(first + rest) == _shape(classic)
        assert thread_graph.get_thread_graph_state(987654) is None
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_memory_checkpoint_db(monkeypatch):
    for value in ("memory", ":memory:"):
        monkeypatch.setenv("GALLAIA_CHECKPOINT_DB", value)
        get_settings.cache_clear()
        thread_graph.reset_runtime()
        assert thread_graph.checkpointer_kind() == "memory"


def test_missing_sqlite_saver_falls_back_to_memory(monkeypatch):
    monkeypatch.setitem(sys.modules, "langgraph.checkpoint.sqlite", None)
    thread_graph.reset_runtime()
    assert thread_graph.checkpointer_kind() == "memory"


def test_graph_state_endpoint(monkeypatch):
    db, _engine = _memory_db()
    client = _client(db)
    try:
        missing = client.get("/api/v1/threads/999999/graph-state")
        assert missing.status_code == 404

        thread_id = _new_thread_with_user_text(client)
        before = client.get(f"/api/v1/threads/{thread_id}/graph-state")
        assert before.status_code == 200
        assert before.json()["thread_id"] == thread_id
        assert before.json()["engine"] == "langgraph"
        assert before.json()["checkpointer"] == "sqlite"
        assert before.json()["state"] is None

        created = advance_thread(
            db, db.get(Thread, thread_id), max_steps=6, llm=_fake_llm
        )
        after = client.get(f"/api/v1/threads/{thread_id}/graph-state")
        assert after.status_code == 200
        body = after.json()
        assert body["checkpointer"] == "sqlite"
        assert body["state"] is not None
        assert body["state"]["created"] == [m.id for m in created]
        assert body["state"]["steps"] == 4
    finally:
        app.dependency_overrides.clear()
        db.close()
