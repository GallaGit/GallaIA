"""Create tables and seed MVP data."""

from sqlalchemy import text

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import (  # noqa: F401
    Agent,
    AgentFsAcl,
    AgentGrant,
    AgentNetworkPolicy,
    AgentSecretRef,
    AgentSession,
    InboxMessage,
    Project,
    Task,
    Skill,
    Goal,
    TaskTemplate,
    TaskTemplateStep,
)
from app.services.seed import ensure_seed_agents_and_grants, seed_if_empty
from app.services.skills import ensure_seed_skills
from app.services.templates import ensure_seed_templates


def _ensure_task_schedule_column() -> None:
    """SQLite create_all does not ADD columns; alter existing tasks table if needed."""
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(tasks)")).fetchall()
        if not rows:
            return
        cols = {r[1] for r in rows}
        if "scheduled_at" not in cols:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN scheduled_at DATETIME"))


def _ensure_session_goal_column() -> None:
    """SQLite create_all does not ADD columns; alter existing sessions if needed."""
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(sessions)")).fetchall()
        if not rows:
            return
        cols = {r[1] for r in rows}
        if "goal_id" not in cols:
            conn.execute(text("ALTER TABLE sessions ADD COLUMN goal_id INTEGER"))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_task_schedule_column()
    _ensure_session_goal_column()
    db = SessionLocal()
    try:
        seed_if_empty(db)
        ensure_seed_agents_and_grants(db)
        ensure_seed_templates(db)
        ensure_seed_skills(db)
    finally:
        db.close()
