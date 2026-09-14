"""Phase 6 slice 1: agentos.yml export/import round-trip."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import selectinload, sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import Base
from app.models import Agent, Project
from app.models.template import TaskTemplate
from app.schemas.agentos_yml import AgentOsYml, AgentYml, TemplateStepYml, TemplateYml
from app.services.agentos_yml import (
    dump_agentos_yml,
    export_agentos_yml,
    import_agentos_yml,
    parse_agentos_yml,
)
from app.services.seed import ensure_seed_agents_and_grants, seed_if_empty


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
    return db


def _project_only_db():
    """Fresh DB with default project but no seed agents/templates."""
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
    db.add(
        Project(
            name="default",
            slug="default",
            description="test",
        )
    )
    db.commit()
    return db


SAMPLE_YAML = """\
version: 1
agents:
  - name: yaml-demo
    title: YAML Demo Agent
    model: claude-sonnet-4
    foundational_prompt: Foundational for yaml-demo.
    role_prompt: Role for yaml-demo.
    runner_preference: mock
templates:
  - slug: yaml-demo-template
    name: YAML Demo Template
    description: Lean Phase 6 fixture
    steps:
      - position: 1
        name: Step one
        description: First
        assignee_agent_name: yaml-demo
        approval_gate: true
        requires_previous_done: false
      - position: 2
        name: Step two
        description: Second
        assignee_agent_name: yaml-demo
        approval_gate: false
        requires_previous_done: true
"""


def test_import_creates_agent_and_template_matching_yaml():
    db = _project_only_db()
    try:
        doc = parse_agentos_yml(SAMPLE_YAML)
        result = import_agentos_yml(db, doc)
        assert result.agents_created == 1
        assert result.templates_created == 1

        agent = db.scalar(select(Agent).where(Agent.name == "yaml-demo"))
        assert agent is not None
        assert agent.title == "YAML Demo Agent"
        assert agent.role_prompt == "Role for yaml-demo."
        assert agent.runner_preference == "mock"

        tmpl = db.scalar(
            select(TaskTemplate)
            .options(selectinload(TaskTemplate.steps))
            .where(TaskTemplate.slug == "yaml-demo-template")
        )
        assert tmpl is not None
        assert tmpl.name == "YAML Demo Template"
        steps = sorted(tmpl.steps, key=lambda s: s.position)
        assert len(steps) == 2
        assert steps[0].approval_gate is True
        assert steps[1].requires_previous_done is True
        assert steps[1].assignee_agent_name == "yaml-demo"
    finally:
        db.close()


def test_import_is_idempotent_by_name_and_slug():
    db = _project_only_db()
    try:
        doc = parse_agentos_yml(SAMPLE_YAML)
        first = import_agentos_yml(db, doc)
        assert first.agents_created == 1
        assert first.templates_created == 1

        # Mutate YAML fields and re-import → update path
        updated = AgentOsYml(
            version=1,
            agents=[
                AgentYml(
                    name="yaml-demo",
                    title="YAML Demo Agent v2",
                    model="claude-opus-4",
                    foundational_prompt="Foundational for yaml-demo.",
                    role_prompt="Updated role",
                    runner_preference="cloud",
                )
            ],
            templates=[
                TemplateYml(
                    slug="yaml-demo-template",
                    name="YAML Demo Template v2",
                    description="Updated",
                    steps=[
                        TemplateStepYml(
                            position=1,
                            name="Only step",
                            approval_gate=False,
                            requires_previous_done=False,
                        )
                    ],
                )
            ],
        )
        second = import_agentos_yml(db, updated)
        assert second.agents_updated == 1
        assert second.agents_created == 0
        assert second.templates_updated == 1
        assert second.templates_created == 0

        agent = db.scalar(select(Agent).where(Agent.name == "yaml-demo"))
        assert agent.title == "YAML Demo Agent v2"
        assert agent.model == "claude-opus-4"
        assert agent.role_prompt == "Updated role"

        tmpl = db.scalar(
            select(TaskTemplate)
            .options(selectinload(TaskTemplate.steps))
            .where(TaskTemplate.slug == "yaml-demo-template")
        )
        assert tmpl.name == "YAML Demo Template v2"
        assert len(tmpl.steps) == 1
        assert tmpl.steps[0].name == "Only step"
    finally:
        db.close()


def test_export_import_round_trip_preserves_agents_and_templates():
    src = _memory_db()
    try:
        exported = export_agentos_yml(src)
        assert len(exported.agents) >= 1
        assert len(exported.templates) >= 1
        yaml_text = dump_agentos_yml(exported)
        parsed = parse_agentos_yml(yaml_text)

        dst = _project_only_db()
        try:
            import_agentos_yml(dst, parsed)
            again = export_agentos_yml(dst)
            assert again.model_dump(exclude_none=True) == parsed.model_dump(
                exclude_none=True
            )
        finally:
            dst.close()
    finally:
        src.close()
