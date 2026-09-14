"""Create tables and seed MVP data."""

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import Agent, AgentGrant, AgentNetworkPolicy, AgentFsAcl, AgentSession, InboxMessage, Project, Task  # noqa: F401
from app.services.seed import ensure_seed_agents_and_grants, seed_if_empty


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
        ensure_seed_agents_and_grants(db)
    finally:
        db.close()
