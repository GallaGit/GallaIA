"""Seed default project + agents on first boot; backfill Isolation grants/network/fs/secrets."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agentos.filesystem import FilesystemAcl
from app.agentos.network import dump_allowlist_json
from app.agentos.secrets import SecretRefSet
from app.agentos.seeds import AGENT_SEEDS, AgentSeed
from app.models import (
    Agent,
    AgentFsAcl,
    AgentGrant,
    AgentNetworkPolicy,
    AgentSecretRef,
    Project,
)


def map_runner_preference(seed_pref: str) -> str:
    """Map seed runner_preference (mock/anthropic/openrouter/inherit) to DB (mock/cloud/local).

    openrouter -> cloud; anthropic -> cloud (legacy); inherit/mock -> mock.
    """
    mapping = {
        "openrouter": "cloud",
        "anthropic": "cloud",  # legacy provider
        "inherit": "mock",
        "mock": "mock",
    }
    try:
        return mapping[seed_pref]
    except KeyError as exc:
        raise ValueError(f"Unknown seed runner_preference {seed_pref!r}") from exc


def _agent_from_seed(project_id: int, seed: AgentSeed) -> Agent:
    return Agent(
        project_id=project_id,
        name=seed.name,
        title=seed.title,
        model=seed.model,
        foundational_prompt=seed.foundational_prompt,
        role_prompt=seed.role_prompt,
        runner_preference=map_runner_preference(seed.runner_preference),
    )


def seed_if_empty(db: Session) -> None:
    existing = db.scalar(select(Project).where(Project.slug == "default"))
    if existing is not None:
        return

    project = Project(
        name="default",
        slug="default",
        description="Proyecto GallaIA v2 por defecto (Orquestador / FE / BE)",
    )
    db.add(project)
    db.flush()

    agents = [_agent_from_seed(project.id, seed) for seed in AGENT_SEEDS.values()]
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
        agent = _agent_from_seed(project.id, seed)
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
    ensure_seed_fs_acls(db, newly_created_ids={agent.id for agent, _ in newly_created})
    ensure_seed_secret_refs(
        db, newly_created_ids={agent.id for agent, _ in newly_created}
    )
    from app.services.templates import ensure_seed_templates
    from app.services.skills import ensure_seed_skills

    ensure_seed_templates(db)
    ensure_seed_skills(db)


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


def _insert_fs_acls(db: Session, agent: Agent, acl: FilesystemAcl) -> None:
    for root in acl.roots:
        db.add(
            AgentFsAcl(
                agent_id=agent.id,
                root=root.root,
                can_read=root.can_read,
                can_write=root.can_write,
                can_delete=root.can_delete,
            )
        )


def ensure_seed_fs_acls(
    db: Session, newly_created_ids: set[int] | None = None
) -> None:
    """Idempotent Isolation backfill: seed filesystem ACLs when the table is empty.

    If ACLs already exist, only newly created agents get seed defaults so an
    operator PUT of `[]` is not overwritten on restart.
    """
    project = db.scalar(select(Project).where(Project.slug == "default"))
    if project is None:
        return

    existing = {
        agent.name: agent
        for agent in db.scalars(select(Agent).where(Agent.project_id == project.id)).all()
    }
    acl_count = db.scalar(select(func.count()).select_from(AgentFsAcl)) or 0
    dirty = False

    if acl_count == 0:
        for seed in AGENT_SEEDS.values():
            agent = existing.get(seed.name)
            if agent is None:
                continue
            _insert_fs_acls(db, agent, seed.filesystem_acl())
            dirty = True
    else:
        created = newly_created_ids or set()
        for seed in AGENT_SEEDS.values():
            agent = existing.get(seed.name)
            if agent is None or agent.id not in created:
                continue
            _insert_fs_acls(db, agent, seed.filesystem_acl())
            dirty = True

    if dirty:
        db.commit()


def _insert_secret_refs(db: Session, agent: Agent, refs: SecretRefSet) -> None:
    for ref in refs.items:
        db.add(
            AgentSecretRef(
                agent_id=agent.id,
                name=ref.name,
                provider=ref.provider,
                key=ref.key,
            )
        )


def ensure_seed_secret_refs(
    db: Session, newly_created_ids: set[int] | None = None
) -> None:
    """Idempotent Isolation backfill: seed secret refs when the table is empty.

    Seeds currently ship with no refs (unresolved refs would deny sessions).
    If rows already exist, only newly created agents get seed defaults so an
    operator PUT of `[]` is not overwritten on restart.
    """
    project = db.scalar(select(Project).where(Project.slug == "default"))
    if project is None:
        return

    existing = {
        agent.name: agent
        for agent in db.scalars(select(Agent).where(Agent.project_id == project.id)).all()
    }
    ref_count = db.scalar(select(func.count()).select_from(AgentSecretRef)) or 0
    dirty = False

    if ref_count == 0:
        for seed in AGENT_SEEDS.values():
            agent = existing.get(seed.name)
            if agent is None:
                continue
            refs = seed.secret_ref_set()
            if not refs.items:
                continue
            _insert_secret_refs(db, agent, refs)
            dirty = True
    else:
        created = newly_created_ids or set()
        for seed in AGENT_SEEDS.values():
            agent = existing.get(seed.name)
            if agent is None or agent.id not in created:
                continue
            refs = seed.secret_ref_set()
            if not refs.items:
                continue
            _insert_secret_refs(db, agent, refs)
            dirty = True

    if dirty:
        db.commit()
