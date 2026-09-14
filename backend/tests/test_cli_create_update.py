"""Phase 6 slice 2: CLI create-agent / update-agent (+ create-template)."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import Base
from app.exceptions import BadRequestError, NotFoundError
from app.models import Agent, Project
from app.models.template import TaskTemplate
from app.schemas.agentos_yml import AgentYml, TemplateStepYml, TemplateYml
from app.services.agentos_yml import (
    create_agent,
    create_agent_from_yml,
    create_template,
    export_agentos_yml,
    update_agent,
)


BACKEND = Path(__file__).resolve().parents[1]


def _project_only_db():
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
    db.add(Project(name="default", slug="default", description="test"))
    db.commit()
    return db


def test_create_agent_matches_export_shape():
    db = _project_only_db()
    try:
        agent = create_agent(
            db,
            name="cli-demo",
            title="CLI Demo",
            role_prompt="Role for cli-demo.",
            model="claude-sonnet-4",
            foundational_prompt="Foundational.",
            runner_preference="mock",
        )
        assert agent.id is not None
        row = db.scalar(select(Agent).where(Agent.name == "cli-demo"))
        assert row is not None
        assert row.title == "CLI Demo"
        assert row.role_prompt == "Role for cli-demo."

        exported = export_agentos_yml(db)
        match = [a for a in exported.agents if a.name == "cli-demo"]
        assert len(match) == 1
        assert match[0].title == "CLI Demo"
        assert match[0].role_prompt == "Role for cli-demo."
        assert match[0].runner_preference == "mock"
    finally:
        db.close()


def test_create_agent_rejects_duplicate_name():
    db = _project_only_db()
    try:
        create_agent(db, name="dup", role_prompt="r1")
        try:
            create_agent(db, name="dup", role_prompt="r2")
            assert False, "expected BadRequestError"
        except BadRequestError as exc:
            assert "already exists" in exc.message
    finally:
        db.close()


def test_update_agent_partial_fields():
    db = _project_only_db()
    try:
        create_agent(
            db,
            name="upd",
            title="Before",
            role_prompt="old role",
            model="claude-sonnet-4",
        )
        updated = update_agent(
            db,
            name="upd",
            title="After",
            role_prompt="new role",
            model="claude-opus-4",
        )
        assert updated.title == "After"
        assert updated.role_prompt == "new role"
        assert updated.model == "claude-opus-4"

        # Unset fields stay
        again = update_agent(db, name="upd", runner_preference="cloud")
        assert again.title == "After"
        assert again.runner_preference == "cloud"
    finally:
        db.close()


def test_update_agent_missing_raises():
    db = _project_only_db()
    try:
        try:
            update_agent(db, name="nope", title="x")
            assert False, "expected NotFoundError"
        except NotFoundError:
            pass
    finally:
        db.close()


def test_create_agent_from_yml_snippet():
    db = _project_only_db()
    try:
        entry = AgentYml(
            name="from-yml",
            title="From YAML",
            model="claude-sonnet-4",
            foundational_prompt="f",
            role_prompt="r",
            runner_preference="local",
        )
        agent = create_agent_from_yml(db, entry)
        assert agent.name == "from-yml"
        assert agent.runner_preference == "local"
    finally:
        db.close()


def test_create_template_lean():
    db = _project_only_db()
    try:
        entry = TemplateYml(
            slug="cli-tmpl",
            name="CLI Template",
            description="lean",
            steps=[
                TemplateStepYml(
                    position=1,
                    name="Only",
                    approval_gate=True,
                    requires_previous_done=False,
                )
            ],
        )
        tmpl = create_template(db, entry)
        assert tmpl.slug == "cli-tmpl"
        row = db.scalar(select(TaskTemplate).where(TaskTemplate.slug == "cli-tmpl"))
        assert row is not None
        assert row.name == "CLI Template"
    finally:
        db.close()


def test_cli_subprocess_create_and_update_agent():
    """Smoke: python -m app.cli create-agent / update-agent against temp SQLite."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "cli.db"
        yaml_out = Path(tmp) / "out.yml"
        env = {
            **os.environ,
            "DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
        }
        # Fresh process must not inherit cached settings from parent
        create = subprocess.run(
            [
                sys.executable,
                "-m",
                "app.cli",
                "create-agent",
                "--name",
                "sub-demo",
                "--role",
                "subprocess role",
                "--title",
                "Sub Demo",
            ],
            cwd=str(BACKEND),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert create.returncode == 0, create.stderr
        assert "Created agent" in create.stdout
        assert "sub-demo" in create.stdout

        update = subprocess.run(
            [
                sys.executable,
                "-m",
                "app.cli",
                "update-agent",
                "--name",
                "sub-demo",
                "--title",
                "Sub Demo v2",
                "--role",
                "updated role",
            ],
            cwd=str(BACKEND),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert update.returncode == 0, update.stderr
        assert "Updated agent" in update.stdout

        export = subprocess.run(
            [
                sys.executable,
                "-m",
                "app.cli",
                "export",
                "-o",
                str(yaml_out),
            ],
            cwd=str(BACKEND),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert export.returncode == 0, export.stderr
        text = yaml_out.read_text(encoding="utf-8")
        assert "sub-demo" in text
        assert "Sub Demo v2" in text
        assert "updated role" in text
