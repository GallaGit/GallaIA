"""Seed default project + agents on first boot."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Agent, Project
from app.services.prompts import FOUNDATIONAL_PROMPT, ROLE_PROMPTS


def seed_if_empty(db: Session) -> None:
    existing = db.scalar(select(Project).where(Project.slug == "default"))
    if existing is not None:
        return

    project = Project(
        name="default",
        slug="default",
        description="Proyecto AgentOS por defecto (MVP Phase 1)",
    )
    db.add(project)
    db.flush()

    agents = [
        Agent(
            project_id=project.id,
            name="default",
            title="Agente por defecto",
            model="claude-sonnet-4",
            foundational_prompt=FOUNDATIONAL_PROMPT,
            role_prompt=ROLE_PROMPTS["default"],
            runner_preference="cloud",
        ),
        Agent(
            project_id=project.id,
            name="plan",
            title="Agente de planificación",
            model="claude-opus-4",
            foundational_prompt=FOUNDATIONAL_PROMPT,
            role_prompt=ROLE_PROMPTS["plan"],
            runner_preference="cloud",
        ),
        Agent(
            project_id=project.id,
            name="senior-dev",
            title="Senior developer",
            model="claude-sonnet-4",
            foundational_prompt=FOUNDATIONAL_PROMPT,
            role_prompt=ROLE_PROMPTS["senior-dev"],
            runner_preference="local",
        ),
    ]
    db.add_all(agents)
    db.commit()
