"""F2.2c — optional human approval before fe/be answer a delegation."""

from __future__ import annotations

import json
import sys
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
from app.models import InboxMessage, Message, Thread  # noqa: E402
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
        "/api/v1/threads", json={"title": "Hilo F2.2c", "created_by": "user"}
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
    """Same kinds/senders/recipients as the classic run (bodies may vary by LLM)."""
    return [(m["sender"], m["recipient"], m["kind"]) for m in messages]


def _messages(client, thread_id):
    return client.get(f"/api/v1/threads/{thread_id}").json()["messages"]


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


def _set_mode(monkeypatch, *, engine: str, approval: bool) -> None:
    monkeypatch.setenv("GALLAIA_THREAD_ENGINE", engine)
    monkeypatch.setenv("GALLAIA_THREAD_APPROVAL", "true" if approval else "false")
    get_settings.cache_clear()


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


def _decide(client, inbox_id: int, approved: bool, note: str | None = None):
    return client.post(
        f"/api/v1/inbox/{inbox_id}/decide",
        json={"approved": approved, "note": note},
    )


def test_a_advance_pauses_and_repeats_are_idempotent(monkeypatch):
    db, _engine = _memory_db()
    client = _client(db)
    try:
        thread_id = _new_thread_with_user_text(client)

        first = advance_thread(db, db.get(Thread, thread_id), max_steps=6, llm=_fake_llm)
        assert [m.sender for m in first] == ["orquestador", "orquestador", "orquestador"]
        assert all(m.kind != "result" for m in first)

        approvals = _open_approvals(db)
        assert len(approvals) == 1
        inbox = approvals[0]
        assert inbox.thread_id == thread_id
        assert inbox.thread_message_id == first[1].id

        state = client.get(f"/api/v1/threads/{thread_id}/graph-state").json()
        assert state["pending_approval"] == inbox.id

        before = _messages(client, thread_id)
        again = advance_thread(db, db.get(Thread, thread_id), max_steps=6, llm=_fake_llm)
        assert again == []
        assert len(_open_approvals(db)) == 1
        assert _messages(client, thread_id) == before
    finally:
        db.close()


def test_b_approved_flow_matches_classic(monkeypatch):
    db, _engine = _memory_db()
    client = _client(db)
    try:
        thread_id = _new_thread_with_user_text(client)
        advance_thread(db, db.get(Thread, thread_id), max_steps=6, llm=_fake_llm)

        while True:
            approvals = _open_approvals(db)
            if not approvals:
                break
            res = _decide(client, approvals[0].id, True)
            assert res.status_code == 200, res.text
            assert res.json()["inbox"]["status"] == "answered"

        final = _messages(client, thread_id)
        assert [m["sender"] for m in final] == [
            "user",
            "orquestador",
            "orquestador",
            "orquestador",
            "fe",
            "be",
            "orquestador",
        ]

        _set_mode(monkeypatch, engine="classic", approval=False)
        classic_thread = _new_thread_with_user_text(client)
        advance_thread(
            db, db.get(Thread, classic_thread), max_steps=6, llm=_fake_llm
        )
        classic = _messages(client, classic_thread)

        assert _shape(final) == _shape(classic)
    finally:
        db.close()


def test_c_rejected_delegation_persists_human_rejection(monkeypatch):
    db, _engine = _memory_db()
    client = _client(db)
    try:
        thread_id = _new_thread_with_user_text(client)
        advance_thread(db, db.get(Thread, thread_id), max_steps=6, llm=_fake_llm)

        approvals = _open_approvals(db)
        assert approvals
        res = _decide(client, approvals[0].id, False, note="no por ahora")
        assert res.status_code == 200, res.text

        rejected = [
            m
            for m in res.json()["created"]
            if m["kind"] == "result" and m["sender"] == approvals[0].body.split(" delega a ")[1].split(":")[0]
        ]
        assert rejected
        assert rejected[0]["body"].startswith("[rechazado por el humano]")
        assert "no por ahora" in rejected[0]["body"]

        answered = db.get(InboxMessage, approvals[0].id)
        assert answered.status == "answered"
        assert answered.reply_body == "no por ahora"

        # the remaining delegations still close the loop with a summary
        while True:
            pending = _open_approvals(db)
            if not pending:
                break
            assert _decide(client, pending[0].id, True).status_code == 200
        final = _messages(client, thread_id)
        assert final[-1]["sender"] == "orquestador"
        assert final[-1]["body"].startswith("Resumen del orquestador")
        assert "[rechazado por el humano]" in final[-1]["body"]
    finally:
        db.close()


def test_d_wrong_endpoints_and_kinds_are_rejected(monkeypatch):
    db, _engine = _memory_db()
    client = _client(db)
    try:
        thread_id = _new_thread_with_user_text(client)
        advance_thread(db, db.get(Thread, thread_id), max_steps=6, llm=_fake_llm)
        approval = _open_approvals(db)[0]

        assert client.post(
            f"/api/v1/inbox/{approval.id}/reply", json={"body": "ok"}
        ).status_code == 400
        assert client.post(
            f"/api/v1/inbox/{approval.id}/resolve", json={"note": "ok"}
        ).status_code == 400

        plain = InboxMessage(
            from_role="agent", kind="text", body="plain decision", status="open"
        )
        db.add(plain)
        db.commit()
        db.refresh(plain)
        assert _decide(client, plain.id, True).status_code == 400

        missing = _decide(client, 999999, True)
        assert missing.status_code == 404
    finally:
        db.close()


def test_e_approval_off_behaves_like_classic(monkeypatch):
    db, _engine = _memory_db()
    client = _client(db)
    try:
        _set_mode(monkeypatch, engine="classic", approval=False)
        classic_thread = _new_thread_with_user_text(client)
        classic = advance_thread(
            db, db.get(Thread, classic_thread), max_steps=6, llm=_fake_llm
        )

        _set_mode(monkeypatch, engine="langgraph", approval=False)
        thread_graph.reset_runtime()
        graph_thread = _new_thread_with_user_text(client)
        graphed = advance_thread(
            db, db.get(Thread, graph_thread), max_steps=6, llm=_fake_llm
        )

        assert [m.sender for m in graphed] == [m.sender for m in classic]
        assert [m.kind for m in graphed] == [m.kind for m in classic]
        assert _open_approvals(db) == []
    finally:
        db.close()


def test_f_sqlite_checkpoint_survives_reset_and_decide(monkeypatch, tmp_path):
    pytest.importorskip("langgraph.checkpoint.sqlite")
    monkeypatch.setenv("GALLAIA_CHECKPOINT_DB", str(tmp_path / "cp.db"))
    get_settings.cache_clear()
    thread_graph.reset_runtime()

    db, _engine = _memory_db()
    client = _client(db)
    try:
        assert thread_graph.checkpointer_kind() == "sqlite"
        thread_id = _new_thread_with_user_text(client)
        advance_thread(db, db.get(Thread, thread_id), max_steps=6, llm=_fake_llm)

        approvals = _open_approvals(db)
        assert len(approvals) == 1
        inbox_id = approvals[0].id
        assert Path(get_settings().checkpoint_db).exists()

        thread_graph.reset_runtime()
        assert thread_graph.pending_approval(thread_id) == inbox_id
        state = client.get(f"/api/v1/threads/{thread_id}/graph-state").json()
        assert state["pending_approval"] == inbox_id

        res = _decide(client, inbox_id, True)
        assert res.status_code == 200, res.text
        assert any(m["kind"] == "result" for m in res.json()["created"])
        assert thread_graph.pending_approval(thread_id) != inbox_id
    finally:
        db.close()
