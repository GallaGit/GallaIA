"""Skills catalog: seed + CRUD. Agent seeds reference skills by slug."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agentos.seeds import AGENT_SEEDS
from app.exceptions import BadRequestError, NotFoundError
from app.models.skill import Skill
from app.schemas.skill import SkillCreate, SkillOut, SkillUpdate, SkillUpsert

PLAN_MODE_SLUG = "plan-mode"

# Seed bodies — reconstructed stubs, not Postma verbatim.
_SKILL_SEEDS: tuple[dict[str, str], ...] = (
    {
        "slug": PLAN_MODE_SLUG,
        "name": "Plan mode",
        "description": (
            "Turn an approved spec into a concrete ordered implementation plan. "
            "Referenced by the plan agent seed."
        ),
        "kind": "prompt",
        "body": (
            "# Plan mode skill\n\n"
            "When this skill is attached, produce a concrete, ordered implementation "
            "plan from the approved specification. Do not implement. Write the plan "
            "onto the task (and as a file attachment if filesystem is granted). "
            "Finish when the plan is complete.\n"
        ),
    },
)


def skill_out(row: Skill) -> SkillOut:
    return SkillOut.model_validate(row)


def ensure_seed_skills(db: Session) -> None:
    """Idempotent seed for catalog skills referenced by agent seeds."""
    dirty = False
    for item in _SKILL_SEEDS:
        existing = db.scalar(select(Skill).where(Skill.slug == item["slug"]))
        if existing is not None:
            continue
        db.add(
            Skill(
                slug=item["slug"],
                name=item["name"],
                description=item["description"],
                kind=item["kind"],
                body=item["body"],
            )
        )
        dirty = True
    if dirty:
        db.commit()


def list_skills(db: Session) -> list[Skill]:
    return list(db.scalars(select(Skill).order_by(Skill.slug)).all())


def get_skill(db: Session, skill_key: str) -> Skill:
    """Resolve by numeric id or slug."""
    row: Skill | None = None
    if skill_key.isdigit():
        row = db.get(Skill, int(skill_key))
    if row is None:
        row = db.scalar(select(Skill).where(Skill.slug == skill_key))
    if row is None:
        raise NotFoundError(f"Skill {skill_key!r} not found")
    return row


def create_skill(db: Session, payload: SkillCreate) -> Skill:
    existing = db.scalar(select(Skill).where(Skill.slug == payload.slug))
    if existing is not None:
        raise BadRequestError(f"Skill slug {payload.slug!r} already exists")
    row = Skill(
        slug=payload.slug,
        name=payload.name,
        description=payload.description,
        kind=payload.kind,
        body=payload.body,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_skill(db: Session, skill_key: str, payload: SkillUpdate) -> Skill:
    row = get_skill(db, skill_key)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise BadRequestError("No fields to update")
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def upsert_skill(db: Session, slug: str, payload: SkillUpsert) -> Skill:
    row = db.scalar(select(Skill).where(Skill.slug == slug))
    if row is None:
        row = Skill(
            slug=slug,
            name=payload.name,
            description=payload.description,
            kind=payload.kind,
            body=payload.body,
        )
        db.add(row)
    else:
        row.name = payload.name
        row.description = payload.description
        row.kind = payload.kind
        row.body = payload.body
    db.commit()
    db.refresh(row)
    return row


def delete_skill(db: Session, skill_key: str) -> None:
    row = get_skill(db, skill_key)
    db.delete(row)
    db.commit()


def resolve_skill_slugs(db: Session, slugs: list[str] | tuple[str, ...]) -> list[Skill]:
    """Minimal glue: resolve agent skill slug refs against the catalog.

    Unknown slugs are skipped (seed may declare ahead of catalog rows).
    """
    if not slugs:
        return []
    rows = db.scalars(select(Skill).where(Skill.slug.in_(list(slugs)))).all()
    by_slug = {r.slug: r for r in rows}
    return [by_slug[s] for s in slugs if s in by_slug]


def agent_seed_skill_slugs() -> set[str]:
    """All skill slugs declared on AgentSeed tuples (for seed/tests)."""
    found: set[str] = set()
    for seed in AGENT_SEEDS.values():
        found.update(seed.skills)
    return found
