"""Seeds single source of truth: seed_if_empty and the backfill agree with AGENT_SEEDS."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401,E402
from app.agentos.seeds import AGENT_SEEDS, DEFAULT_AGENT_MODEL  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.models import Agent, Project  # noqa: E402
from app.services.seed import (  # noqa: E402
    ensure_seed_agents_and_grants,
    map_runner_preference,
    seed_if_empty,
)


def _session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _snapshot(db) -> dict[str, tuple[str, str, str]]:
    return {
        a.name: (a.title, a.model, a.runner_preference)
        for a in db.scalars(select(Agent)).all()
    }


@pytest.mark.parametrize(
    ("pref", "expected"),
    [("openrouter", "cloud"), ("anthropic", "cloud"), ("inherit", "mock"), ("mock", "mock")],
)
def test_map_runner_preference(pref: str, expected: str) -> None:
    assert map_runner_preference(pref) == expected


def test_map_runner_preference_unknown_raises() -> None:
    with pytest.raises(ValueError):
        map_runner_preference("groq")


def test_seed_paths_agree() -> None:
    a = _session()
    seed_if_empty(a)
    via_seed = _snapshot(a)

    b = _session()
    b.add(Project(name="default", slug="default", description="x"))
    b.commit()
    ensure_seed_agents_and_grants(b)
    via_backfill = _snapshot(b)

    assert set(via_seed) == {"orquestador", "fe", "be"}
    assert via_seed == via_backfill
    for name, seed in AGENT_SEEDS.items():
        assert via_seed[name] == (
            seed.title,
            seed.model,
            map_runner_preference(seed.runner_preference),
        )
    assert via_seed["orquestador"][1] == DEFAULT_AGENT_MODEL
    assert via_seed["orquestador"][2] == "cloud"
