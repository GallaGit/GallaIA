"""Isolation filesystem wall: per-agent roots, deny peer folders and `../`."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agentos.filesystem import (
    FilesystemAcl,
    FsRoot,
    MockFilesystem,
    evaluate_fs,
    gated_fs_output,
    has_traversal,
)
from app.agentos.models import Task
from app.agentos.runner import SessionRunner
from app.agentos.seeds import get_seed
from app.agentos.store import AgentOSStore
from app.core.config import get_settings
from app.db.base import Base
from app.models import Agent, AgentFsAcl, Project
from app.models.task import Task as DbTask
from app.schemas.filesystem import FsRootItem
from app.services.filesystem import filesystem_acl_for_agent, fs_out, replace_agent_fs
from app.services.runner import run_task_session
from app.services.seed import ensure_seed_agents_and_grants, seed_if_empty


def _clear_llm_env(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    get_settings.cache_clear()


def _memory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
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
    return db


def test_empty_acl_default_deny():
    acl = FilesystemAcl.empty()
    denied = evaluate_fs(acl, "read", "/agents/support/ticket.md")
    assert denied.allowed is False
    assert "outside allowed roots" in denied.reason


def test_allow_own_folder_deny_peer():
    support = FilesystemAcl.for_agent("support")
    own = evaluate_fs(support, "read", "/agents/support/ticket.md")
    assert own.allowed is True
    peer = evaluate_fs(support, "read", "/agents/senior-dev/notes.md")
    assert peer.allowed is False
    assert "outside allowed roots" in peer.reason
    # Prefix-not-boundary: /agents/support-other is not under /agents/support
    sneak = evaluate_fs(support, "read", "/agents/support-other/x")
    assert sneak.allowed is False


def test_traversal_denied_even_if_resolved_stays_in_root():
    acl = FilesystemAcl.for_agent("support")
    assert has_traversal("/agents/support/../senior-dev/notes.md")
    assert has_traversal("..\\senior-dev\\notes.md")
    denied = evaluate_fs(acl, "read", "/agents/support/../senior-dev/notes.md")
    assert denied.allowed is False
    assert denied.traversal is True
    assert "traversal" in denied.reason
    still_in_root = evaluate_fs(acl, "read", "/agents/support/foo/../ticket.md")
    assert still_in_root.allowed is False
    assert still_in_root.traversal is True


def test_write_does_not_imply_delete():
    acl = FilesystemAcl.from_roots(
        (FsRoot("/agents/support", can_read=True, can_write=True, can_delete=False),)
    )
    assert evaluate_fs(acl, "write", "/agents/support/note.txt").allowed is True
    delete = evaluate_fs(acl, "delete", "/agents/support/note.txt")
    assert delete.allowed is False
    assert "delete denied" in delete.reason


def test_gated_output_does_not_leak_peer_content():
    store = MockFilesystem.seeded()
    support = FilesystemAcl.for_agent("support")
    allowed = gated_fs_output(support, "read", "/agents/support/ticket.md", store=store)
    assert allowed["ok"] is True
    assert allowed["content"] == "Front ticket #1"
    denied = gated_fs_output(
        support, "read", "/agents/senior-dev/notes.md", store=store
    )
    assert denied["ok"] is False
    assert denied["denied"] is True
    assert "private senior-dev notes" not in str(denied)
    traversal = gated_fs_output(
        support, "read", "/agents/support/../senior-dev/notes.md", store=store
    )
    assert traversal["denied"] is True
    assert traversal["fs"]["traversal"] is True
    assert "private senior-dev notes" not in str(traversal)


def test_support_seed_cannot_read_senior_dev_folder():
    support = get_seed("support").filesystem_acl()
    senior = get_seed("senior-dev").filesystem_acl()
    assert support.roots[0].root == "/agents/support"
    assert senior.roots[0].root == "/agents/senior-dev"
    assert evaluate_fs(support, "read", "/agents/support/ticket.md").allowed
    assert not evaluate_fs(support, "read", "/agents/senior-dev/notes.md").allowed
    assert evaluate_fs(senior, "read", "/agents/senior-dev/notes.md").allowed
    assert not evaluate_fs(senior, "read", "/agents/support/ticket.md").allowed


def test_support_mock_fs_allow_deny_traversal(monkeypatch):
    _clear_llm_env(monkeypatch)
    store = AgentOSStore()
    task = store.create_task(
        Task(name="Reset password", description="Front ticket", assignee_agent="support")
    )
    result = SessionRunner(store).run(task.id, runner="mock")
    reads = [e for e in result.tool_events if e.name == "fs.read"]
    assert len(reads) == 3
    by_path = {e.input["path"]: e for e in reads}
    own = by_path["/agents/support/ticket.md"]
    assert own.output.get("ok") is True
    assert own.output.get("denied") is not True
    assert own.output.get("content") == "Front ticket #1"
    peer = by_path["/agents/senior-dev/notes.md"]
    assert peer.output.get("ok") is False
    assert peer.output.get("denied") is True
    assert "private senior-dev notes" not in str(peer.output)
    traversal = by_path["/agents/support/../senior-dev/notes.md"]
    assert traversal.output.get("denied") is True
    assert traversal.output.get("fs", {}).get("traversal") is True
    assert "private senior-dev notes" not in str(traversal.output)


def test_senior_dev_mock_fs_allows_own(monkeypatch):
    _clear_llm_env(monkeypatch)
    store = AgentOSStore()
    task = store.create_task(Task(name="Fix bug", assignee_agent="senior-dev"))
    result = SessionRunner(store).run(task.id, runner="mock")
    reads = [e for e in result.tool_events if e.name == "fs.read"]
    assert len(reads) == 1
    assert reads[0].input["path"] == "/agents/senior-dev/notes.md"
    assert reads[0].output.get("ok") is True
    assert reads[0].output.get("content") == "private senior-dev notes"


def test_sqlite_support_fs_api():
    db = _memory_db()
    try:
        support = db.scalar(select(Agent).where(Agent.name == "support"))
        senior = db.scalar(select(Agent).where(Agent.name == "senior-dev"))
        assert support is not None and senior is not None
        acl = filesystem_acl_for_agent(support)
        assert acl.roots[0].root == "/agents/support"
        assert evaluate_fs(acl, "read", "/agents/support/x").allowed
        assert not evaluate_fs(acl, "read", "/agents/senior-dev/x").allowed
        listed = fs_out(support)
        assert listed.agent_name == "support"
        assert listed.roots[0].root == "/agents/support"
        assert listed.roots[0].can_read is True

        replace_agent_fs(
            db,
            support,
            [FsRootItem(root="/agents/support", can_read=True, can_write=False, can_delete=False)],
        )
        db.refresh(support)
        updated = filesystem_acl_for_agent(support)
        assert updated.roots[0].can_write is False
        assert evaluate_fs(updated, "read", "/agents/support/x").allowed
        assert not evaluate_fs(updated, "write", "/agents/support/x").allowed

        replace_agent_fs(db, support, [])
        db.refresh(support)
        assert filesystem_acl_for_agent(support).roots == ()
        assert db.scalar(select(AgentFsAcl).where(AgentFsAcl.agent_id == support.id)) is None
    finally:
        db.close()


def test_sqlite_mock_runner_support_cannot_read_peer(monkeypatch):
    _clear_llm_env(monkeypatch)
    db = _memory_db()
    try:
        project = db.scalar(select(Project).where(Project.slug == "default"))
        support = db.scalar(select(Agent).where(Agent.name == "support"))
        task = DbTask(
            project_id=project.id,
            name="Front ticket",
            assignee_agent_id=support.id,
            status="todo",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        session = run_task_session(db, task, support)
        fs_events = [
            row for row in session.get_tool_events() if str(row.get("tool", "")).startswith("fs.")
        ]
        assert len(fs_events) == 3
        details = [row.get("detail", "") for row in fs_events]
        assert any("/agents/support/ticket.md" in d and "DENIED" not in d for d in details)
        peer = next(d for d in details if "/agents/senior-dev/notes.md" in d and "../" not in d)
        assert "DENIED" in peer
        traversal = next(d for d in details if "../" in d)
        assert "DENIED" in traversal
        assert "traversal" in traversal
    finally:
        db.close()
