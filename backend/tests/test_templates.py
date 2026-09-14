"""Phase 3 Templates: instantiate + prior-step gate (demo + compound)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.db.base import Base
from app.exceptions import BadRequestError
from app.models import Agent, Task, TaskTemplate
from app.services.runner import run_task_session
from app.services.seed import ensure_seed_agents_and_grants, seed_if_empty
from app.services.templates import (
    COMPOUND_ENGINEER_SLUG,
    DEMO_TWO_STEP_SLUG,
    assert_prior_step_done,
    get_template,
    instantiate_template,
    list_templates,
)


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


def test_demo_two_step_seed_present():
    db = _memory_db()
    try:
        templates = list_templates(db)
        slugs = {t.slug for t in templates}
        assert DEMO_TWO_STEP_SLUG in slugs
        demo = get_template(db, DEMO_TWO_STEP_SLUG)
        assert demo.name
        steps = sorted(demo.steps, key=lambda s: s.position)
        assert len(steps) == 2
        assert steps[0].position == 1
        assert steps[0].approval_gate is True
        assert steps[0].requires_previous_done is False
        assert steps[1].position == 2
        assert steps[1].requires_previous_done is True
    finally:
        db.close()


def test_instantiate_creates_two_cards_with_dependency():
    db = _memory_db()
    try:
        template = get_template(db, DEMO_TWO_STEP_SLUG)
        result = instantiate_template(db, template)
        assert result.template_slug == DEMO_TWO_STEP_SLUG
        assert len(result.tasks) == 2
        t1, t2 = result.tasks
        assert t1.step_index == 1
        assert t2.step_index == 2
        assert t1.depends_on_task_id is None
        assert t2.depends_on_task_id == t1.id
        assert t1.approval_gate is True
        assert t2.approval_gate is False
        assert t1.template_run_id == t2.template_run_id == result.run_id
        assert t1.status == "todo" and t2.status == "todo"

        plan = db.scalar(select(Agent).where(Agent.name == "plan"))
        senior = db.scalar(select(Agent).where(Agent.name == "senior-dev"))
        assert plan is not None and senior is not None
        assert t1.assignee_agent_id == plan.id
        assert t2.assignee_agent_id == senior.id
    finally:
        db.close()


def test_step2_gate_blocks_run_until_step1_done(monkeypatch):
    _clear_llm_env(monkeypatch)
    db = _memory_db()
    try:
        template = get_template(db, DEMO_TWO_STEP_SLUG)
        result = instantiate_template(db, template)
        t1 = db.get(Task, result.tasks[0].id)
        t2 = db.get(Task, result.tasks[1].id)
        assert t1 is not None and t2 is not None

        with pytest.raises(BadRequestError) as blocked:
            assert_prior_step_done(db, t2)
        assert "blocked" in blocked.value.message.lower()

        agent2 = db.get(Agent, t2.assignee_agent_id)
        assert agent2 is not None
        with pytest.raises(BadRequestError):
            run_task_session(db, t2, agent2)

        # Human marks step 1 done (approval gate).
        t1.status = "done"
        db.commit()

        assert_prior_step_done(db, t2)  # no raise
        session = run_task_session(db, t2, agent2)
        assert session.status == "destroyed"
        db.refresh(t2)
        assert t2.status == "done"
    finally:
        db.close()


def test_instantiate_idempotent_seed():
    db = _memory_db()
    try:
        count_before = db.scalar(select(TaskTemplate))
        assert count_before is not None
        from app.services.templates import ensure_seed_templates

        ensure_seed_templates(db)
        ensure_seed_templates(db)
        rows = list(
            db.scalars(
                select(TaskTemplate).where(TaskTemplate.slug == DEMO_TWO_STEP_SLUG)
            ).all()
        )
        assert len(rows) == 1
        compound_rows = list(
            db.scalars(
                select(TaskTemplate).where(TaskTemplate.slug == COMPOUND_ENGINEER_SLUG)
            ).all()
        )
        assert len(compound_rows) == 1
    finally:
        db.close()


def test_compound_engineer_seed_nine_steps():
    db = _memory_db()
    try:
        templates = list_templates(db)
        slugs = {t.slug for t in templates}
        assert COMPOUND_ENGINEER_SLUG in slugs
        tpl = get_template(db, COMPOUND_ENGINEER_SLUG)
        steps = sorted(tpl.steps, key=lambda s: s.position)
        assert len(steps) == 9
        assert [s.position for s in steps] == list(range(1, 10))
        assert steps[0].requires_previous_done is False
        assert steps[0].approval_gate is True
        for step in steps[1:]:
            assert step.requires_previous_done is True
        assert steps[8].approval_gate is True
        assert steps[8].position == 9
    finally:
        db.close()


def test_compound_instantiate_nine_cards_and_gates():
    db = _memory_db()
    try:
        template = get_template(db, COMPOUND_ENGINEER_SLUG)
        result = instantiate_template(db, template)
        assert result.template_slug == COMPOUND_ENGINEER_SLUG
        assert len(result.tasks) == 9
        tasks = result.tasks
        assert tasks[0].depends_on_task_id is None
        for i in range(1, 9):
            assert tasks[i].step_index == i + 1
            assert tasks[i].depends_on_task_id == tasks[i - 1].id
            assert tasks[i].template_run_id == result.run_id

        t1 = db.get(Task, tasks[0].id)
        t2 = db.get(Task, tasks[1].id)
        t3 = db.get(Task, tasks[2].id)
        assert t1 is not None and t2 is not None and t3 is not None

        with pytest.raises(BadRequestError) as blocked2:
            assert_prior_step_done(db, t2)
        assert "blocked" in blocked2.value.message.lower()

        with pytest.raises(BadRequestError) as blocked3:
            assert_prior_step_done(db, t3)
        assert "blocked" in blocked3.value.message.lower()

        t1.status = "done"
        db.commit()
        assert_prior_step_done(db, t2)  # no raise

        with pytest.raises(BadRequestError):
            assert_prior_step_done(db, t3)

        t2.status = "done"
        db.commit()
        assert_prior_step_done(db, t3)  # no raise
    finally:
        db.close()
