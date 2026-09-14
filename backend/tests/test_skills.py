"""Phase 3 Skills catalog: seed + CRUD."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import Base
from app.exceptions import BadRequestError, NotFoundError
from app.models.skill import Skill
from app.schemas.skill import SkillCreate, SkillUpdate, SkillUpsert
from app.services.seed import ensure_seed_agents_and_grants, seed_if_empty
from app.services.skills import (
    PLAN_MODE_SLUG,
    agent_seed_skill_slugs,
    create_skill,
    delete_skill,
    ensure_seed_skills,
    get_skill,
    list_skills,
    resolve_skill_slugs,
    update_skill,
    upsert_skill,
)


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
    ensure_seed_skills(db)
    return db


def test_plan_mode_seed_present():
    db = _memory_db()
    try:
        skill = get_skill(db, PLAN_MODE_SLUG)
        assert skill.slug == PLAN_MODE_SLUG
        assert skill.name
        assert skill.kind == "prompt"
        assert "plan" in skill.body.lower() or "implementation" in skill.body.lower()
        slugs = {s.slug for s in list_skills(db)}
        assert PLAN_MODE_SLUG in slugs
    finally:
        db.close()


def test_agent_seed_skill_slugs_resolve_in_catalog():
    """Minimal glue: AgentSeed.skills strings are catalog slugs, not bare orphans."""
    db = _memory_db()
    try:
        declared = agent_seed_skill_slugs()
        assert PLAN_MODE_SLUG in declared
        resolved = resolve_skill_slugs(db, sorted(declared))
        assert {r.slug for r in resolved} == declared
    finally:
        db.close()


def test_ensure_seed_skills_idempotent():
    db = _memory_db()
    try:
        before = db.scalar(select(Skill).where(Skill.slug == PLAN_MODE_SLUG))
        assert before is not None
        body_before = before.body
        ensure_seed_skills(db)
        after = db.scalar(select(Skill).where(Skill.slug == PLAN_MODE_SLUG))
        assert after is not None
        assert after.id == before.id
        assert after.body == body_before
        assert len(list_skills(db)) >= 1
    finally:
        db.close()


def test_create_get_update_delete():
    db = _memory_db()
    try:
        created = create_skill(
            db,
            SkillCreate(
                slug="code-review-lite",
                name="Code review lite",
                description="Short review checklist",
                kind="prompt",
                body="Review for bugs and clarity.",
            ),
        )
        assert created.id > 0
        got = get_skill(db, "code-review-lite")
        assert got.body == "Review for bugs and clarity."
        by_id = get_skill(db, str(created.id))
        assert by_id.slug == "code-review-lite"

        updated = update_skill(
            db,
            "code-review-lite",
            SkillUpdate(body="Review for bugs, clarity, and tests."),
        )
        assert "tests" in updated.body

        delete_skill(db, "code-review-lite")
        with pytest.raises(NotFoundError):
            get_skill(db, "code-review-lite")
    finally:
        db.close()


def test_create_duplicate_slug_rejected():
    db = _memory_db()
    try:
        with pytest.raises(BadRequestError):
            create_skill(
                db,
                SkillCreate(
                    slug=PLAN_MODE_SLUG,
                    name="Dup",
                    body="x",
                ),
            )
    finally:
        db.close()


def test_upsert_creates_and_replaces():
    db = _memory_db()
    try:
        row = upsert_skill(
            db,
            "support-front",
            SkillUpsert(
                name="Support Front",
                description="Front-only support cues",
                kind="prompt",
                body="Use Front MCP only.",
            ),
        )
        assert row.slug == "support-front"
        assert "Front" in row.body
        again = upsert_skill(
            db,
            "support-front",
            SkillUpsert(
                name="Support Front v2",
                kind="prompt",
                body="Use Front MCP only. No GitHub.",
            ),
        )
        assert again.id == row.id
        assert again.name == "Support Front v2"
        assert "No GitHub" in again.body
    finally:
        db.close()


def test_get_unknown_raises():
    db = _memory_db()
    try:
        with pytest.raises(NotFoundError):
            get_skill(db, "no-such-skill")
    finally:
        db.close()
