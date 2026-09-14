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


def _ensure_goal_rails_columns() -> None:
    """SQLite create_all does not ADD columns; alter existing goals if needed."""
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(goals)")).fetchall()
        if not rows:
            return
        cols = {r[1] for r in rows}
        alters = []
        if "dod_checked_json" not in cols:
            alters.append("ALTER TABLE goals ADD COLUMN dod_checked_json TEXT DEFAULT '[]'")
        if "spend_cap" not in cols:
            alters.append("ALTER TABLE goals ADD COLUMN spend_cap FLOAT")
        if "spend_accrued" not in cols:
            alters.append("ALTER TABLE goals ADD COLUMN spend_accrued FLOAT DEFAULT 0")
        if "max_wall_seconds" not in cols:
            alters.append("ALTER TABLE goals ADD COLUMN max_wall_seconds INTEGER")
        if "stuck_threshold" not in cols:
            alters.append("ALTER TABLE goals ADD COLUMN stuck_threshold INTEGER DEFAULT 19")
        if "activated_at" not in cols:
            alters.append("ALTER TABLE goals ADD COLUMN activated_at DATETIME")
        for stmt in alters:
            conn.execute(text(stmt))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_task_schedule_column()
    _ensure_session_goal_column()
    _ensure_goal_rails_columns()
    db = SessionLocal()
    try:
        seed_if_empty(db)
        ensure_seed_agents_and_grants(db)
        ensure_seed_templates(db)
        ensure_seed_skills(db)
    finally:
        db.close()
