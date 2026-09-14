"""Phase 3 schedule-at: set/clear + demo tick (no cron runner)."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import Base
from app.models import Agent, AgentSession, Project, Task
from app.services.scheduler import set_task_schedule, tick_scheduler
from app.services.seed import ensure_seed_agents_and_grants, seed_if_empty


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


def _make_task(db, *, name: str = "scheduled", assignee: bool = True) -> Task:
    project = db.scalar(select(Project).where(Project.slug == "default"))
    assert project is not None
    agent_id = None
    if assignee:
        agent = db.scalar(select(Agent).where(Agent.name == "default"))
        assert agent is not None
        agent_id = agent.id
    task = Task(
        project_id=project.id,
        name=name,
        status="todo",
        assignee_agent_id=agent_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def test_future_schedule_not_due_on_tick():
    db = _memory_db()
    try:
        task = _make_task(db, name="future")
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        set_task_schedule(db, task, future)
        db.refresh(task)
        assert task.scheduled_at is not None

        result = tick_scheduler(db, now=datetime.now(timezone.utc))
        assert result["promoted_count"] == 0
        assert result["promoted_task_ids"] == []
        db.refresh(task)
        assert task.scheduled_at is not None
        sessions = list(db.scalars(select(AgentSession).where(AgentSession.task_id == task.id)).all())
        assert sessions == []
    finally:
        db.close()


def test_past_schedule_promoted_by_tick_creates_session_stub():
    db = _memory_db()
    try:
        task = _make_task(db, name="due")
        past = datetime.now(timezone.utc) - timedelta(minutes=5)
        set_task_schedule(db, task, past)

        clock = datetime.now(timezone.utc)
        result = tick_scheduler(db, now=clock)
        assert result["promoted_count"] == 1
        assert result["promoted_task_ids"] == [task.id]
        assert len(result["session_ids"]) == 1

        db.refresh(task)
        assert task.scheduled_at is None
        assert task.status == "todo"  # runnable; stub queued separately

        stub = db.get(AgentSession, result["session_ids"][0])
        assert stub is not None
        assert stub.task_id == task.id
        assert stub.runner == "scheduler"
        assert stub.status == "queued"
        assert stub.summary and "scheduler" in stub.summary.lower()
    finally:
        db.close()


def test_clear_schedule():
    db = _memory_db()
    try:
        task = _make_task(db, name="clear-me")
        set_task_schedule(db, task, datetime.now(timezone.utc) + timedelta(days=1))
        db.refresh(task)
        assert task.scheduled_at is not None
        set_task_schedule(db, task, None)
        db.refresh(task)
        assert task.scheduled_at is None
    finally:
        db.close()


def test_tick_without_assignee_clears_schedule_no_session():
    db = _memory_db()
    try:
        task = _make_task(db, name="orphan", assignee=False)
        set_task_schedule(db, task, datetime.now(timezone.utc) - timedelta(seconds=1))
        result = tick_scheduler(db, now=datetime.now(timezone.utc))
        assert result["promoted_task_ids"] == [task.id]
        assert result["session_ids"] == []
        db.refresh(task)
        assert task.scheduled_at is None
    finally:
        db.close()


@pytest.mark.skip(
    reason="cron string runner deferred to Phase 5 automations; this slice is schedule_at only"
)
def test_invalid_cron_rejected():
    """Placeholder: reject invalid cron when Phase 5 stores a cron field."""
    raise AssertionError("unreachable — cron not in this slice")
