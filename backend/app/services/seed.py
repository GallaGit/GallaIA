"""Seed default project + agents on first boot; backfill Isolation grants/network."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agentos.network import dump_allowlist_json
from app.agentos.seeds import AGENT_SEEDS, AgentSeed
from app.models import Agent, AgentGrant, AgentNetworkPolicy, Project
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
        Agent(
            project_id=project.id,
            name="support",
            title="Customer support",
            model="claude-sonnet-4",
            foundational_prompt=FOUNDATIONAL_PROMPT,
            role_prompt=ROLE_PROMPTS["support"],
            runner_preference="mock",
        ),
    ]
    db.add_all(agents)
    db.commit()


def _insert_grants(db: Session, agent: Agent, pairs: tuple[tuple[str, str], ...]) -> None:
    for kind, name in pairs:
        db.add(AgentGrant(agent_id=agent.id, kind=kind, name=name))


def ensure_seed_agents_and_grants(db: Session) -> None:
    """Idempotent Isolation backfill: missing seed agents + default grants.

    If the grants table is empty (first Isolation boot), seed grants for every
    known agent. If it already has rows, only new agents get default grants so
    an operator PUT of `[]` is not overwritten on restart.
    """
    project = db.scalar(select(Project).where(Project.slug == "default"))
    if project is None:
        return

    existing = {
        agent.name: agent
        for agent in db.scalars(select(Agent).where(Agent.project_id == project.id)).all()
    }
    grant_count = db.scalar(select(func.count()).select_from(AgentGrant)) or 0
    newly_created: list[tuple[Agent, tuple[tuple[str, str], ...]]] = []
    dirty = False

    for seed in AGENT_SEEDS.values():
        if seed.name in existing:
            continue
        agent = Agent(
            project_id=project.id,
            name=seed.name,
            title=seed.title,
            model=seed.model,
            foundational_prompt=seed.foundational_prompt,
            role_prompt=seed.role_prompt,
            runner_preference=seed.runner_preference
            if seed.runner_preference in {"mock", "cloud", "local"}
            else "mock",
        )
        db.add(agent)
        db.flush()
        existing[seed.name] = agent
        newly_created.append((agent, seed.grants))
        dirty = True

    if grant_count == 0:
        for seed in AGENT_SEEDS.values():
            agent = existing.get(seed.name)
            if agent is None:
                continue
            _insert_grants(db, agent, seed.grants)
        dirty = True
    else:
        for agent, pairs in newly_created:
            _insert_grants(db, agent, pairs)

    if dirty:
        db.commit()
    ensure_seed_network_policies(db)


def _upsert_network_policy(db: Session, agent: Agent, seed: AgentSeed) -> None:
    db.add(
        AgentNetworkPolicy(
            agent_id=agent.id,
            mode=seed.network_mode,
            allowlist_json=dump_allowlist_json(seed.network_allowlist),
        )
    )


def ensure_seed_network_policies(db: Session) -> None:
    """Idempotent Isolation backfill: seed network policy when the table is empty.

    If policies already exist, only agents without a row get seed defaults so an
    operator PUT is not overwritten on restart.
    """
    project = db.scalar(select(Project).where(Project.slug == "default"))
    if project is None:
        return

    existing = {
        agent.name: agent
        for agent in db.scalars(select(Agent).where(Agent.project_id == project.id)).all()
    }
    policy_count = db.scalar(select(func.count()).select_from(AgentNetworkPolicy)) or 0
    dirty = False

    if policy_count == 0:
        for seed in AGENT_SEEDS.values():
            agent = existing.get(seed.name)
            if agent is None:
                continue
            _upsert_network_policy(db, agent, seed)
            dirty = True
    else:
        have = {
            row.agent_id
            for row in db.scalars(select(AgentNetworkPolicy)).all()
        }
        for seed in AGENT_SEEDS.values():
            agent = existing.get(seed.name)
            if agent is None or agent.id in have:
                continue
            _upsert_network_policy(db, agent, seed)
            dirty = True

    if dirty:
        db.commit()
