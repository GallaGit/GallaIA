"""Create tables and seed MVP data."""

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
    TaskTemplate,
    TaskTemplateStep,
)
from app.services.seed import ensure_seed_agents_and_grants, seed_if_empty
from app.services.templates import ensure_seed_templates


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
        ensure_seed_agents_and_grants(db)
        ensure_seed_templates(db)
    finally:
        db.close()
