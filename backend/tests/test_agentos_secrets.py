"""Isolation secret-refs wall: persist pointers only; resolve at session start."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agentos.models import Task
from app.agentos.runner import SessionRunner
from app.agentos.secrets import (
    SecretRef,
    SecretRefSet,
    UnresolvedSecretRef,
    looks_like_raw_secret,
    resolve_secret_refs,
)
from app.agentos.store import AgentOSStore
from app.core.config import get_settings
from app.db.base import Base
from app.exceptions import BadRequestError, UnresolvedSecretRefError
from app.models import Agent, AgentSecretRef, Project
from app.models.task import Task as DbTask
from app.schemas.secret import AgentSecretsUpdate, SecretRefItem
from app.services.runner import run_task_session
from app.services.secrets import (
    replace_agent_secrets,
    resolve_agent_secrets,
    secret_refs_for_agent,
    secrets_out,
)
from app.services.seed import ensure_seed_agents_and_grants, seed_if_empty

FIXTURE_VALUE = "gallaia-fixture-plaintext-NEVER-IN-DB"
ENV_KEY = "GALLAIA_TEST_SECRET_FOO"


def _clear_llm_env(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    get_settings.cache_clear()


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


def _sqlite_dump(db) -> str:
    chunks: list[str] = []
    for table in Base.metadata.sorted_tables:
        rows = db.execute(select(table)).fetchall()
        chunks.append(f"{table.name}={rows!r}")
    return "\n".join(chunks)


def test_looks_like_raw_secret_rejects_tokens():
    assert looks_like_raw_secret("sk-ant-api03-not-a-real-key")
    assert looks_like_raw_secret("ghp_abcdefghijklmnopqrstuvwxyz0123456789")
    assert looks_like_raw_secret("FOO=super-secret-value")
    assert not looks_like_raw_secret("GALLAIA_TEST_SECRET_FOO")
    assert not looks_like_raw_secret("FOO")


def test_resolve_from_env_fixture():
    refs = SecretRefSet.from_items(
        (SecretRef(name="FOO", provider="env", key=ENV_KEY),)
    )
    runtime = resolve_secret_refs(refs, fixture={ENV_KEY: FIXTURE_VALUE})
    assert runtime.get("FOO") == FIXTURE_VALUE
    assert "FOO" in runtime.as_public_dict()["injected"]
    assert FIXTURE_VALUE not in json.dumps(runtime.as_public_dict())


def test_unresolved_ref_raises():
    refs = SecretRefSet.from_items(
        (SecretRef(name="FOO", provider="env", key=ENV_KEY),)
    )
    with pytest.raises(UnresolvedSecretRef) as exc:
        resolve_secret_refs(refs, environ={}, fixture={})
    assert "FOO" in str(exc.value)
    assert exc.value.missing == ("FOO",)


def test_schema_forbids_value_field():
    with pytest.raises(ValidationError):
        SecretRefItem.model_validate(
            {"name": "FOO", "provider": "env", "key": ENV_KEY, "value": FIXTURE_VALUE}
        )
    with pytest.raises(ValidationError):
        AgentSecretsUpdate.model_validate(
            {"secrets": [{"name": "FOO", "value": FIXTURE_VALUE}]}
        )


def test_sqlite_rejects_raw_looking_key_and_persists_refs_only():
    db = _memory_db()
    try:
        support = db.scalar(select(Agent).where(Agent.name == "support"))
        assert support is not None
        listed = secrets_out(support)
        assert listed.secrets == []

        with pytest.raises(BadRequestError, match="raw secret"):
            replace_agent_secrets(
                db,
                support,
                [
                    SecretRefItem(
                        name="FOO",
                        provider="env",
                        key="sk-ant-api03-not-a-real-key",
                    )
                ],
            )

        replace_agent_secrets(
            db,
            support,
            [SecretRefItem(name="FOO", provider="env", key=ENV_KEY)],
        )
        db.refresh(support)
        refs = secret_refs_for_agent(support)
        assert refs.as_list() == [
            {"name": "FOO", "provider": "env", "key": ENV_KEY}
        ]
        row = db.scalar(select(AgentSecretRef).where(AgentSecretRef.agent_id == support.id))
        assert row is not None
        assert row.name == "FOO"
        assert row.key == ENV_KEY
        assert FIXTURE_VALUE not in (row.name, row.key, row.provider)

        dump = _sqlite_dump(db)
        assert FIXTURE_VALUE not in dump
        assert "sk-ant-api03-not-a-real-key" not in dump
    finally:
        db.close()


def test_session_resolves_from_env_and_db_has_no_plaintext(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv(ENV_KEY, FIXTURE_VALUE)
    store = AgentOSStore()
    task = store.create_task(
        Task(name="Reset password", description="Front ticket", assignee_agent="support")
    )
    refs = SecretRefSet.from_items(
        (SecretRef(name="FOO", provider="env", key=ENV_KEY),)
    )
    result = SessionRunner(store).run(task.id, runner="mock", secrets=refs)
    assert result.secrets.get("FOO") == FIXTURE_VALUE
    inject = next(e for e in result.tool_events if e.name == "session.secrets")
    assert inject.output.get("injected") == ["FOO"]
    assert FIXTURE_VALUE not in json.dumps(inject.output)
    get_evt = next(e for e in result.tool_events if e.name == "secret.get")
    assert get_evt.output.get("ok") is True
    assert get_evt.output.get("present") is True
    assert "value" not in get_evt.output
    blob = json.dumps(
        [
            {"name": e.name, "input": e.input, "output": e.output}
            for e in result.tool_events
        ]
    )
    assert FIXTURE_VALUE not in blob
    assert ENV_KEY in blob


def test_unresolved_ref_denies_session(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.delenv(ENV_KEY, raising=False)
    store = AgentOSStore()
    task = store.create_task(Task(name="Front ticket", assignee_agent="support"))
    refs = SecretRefSet.from_items(
        (SecretRef(name="FOO", provider="env", key=ENV_KEY),)
    )
    with pytest.raises(UnresolvedSecretRef) as exc:
        SessionRunner(store).run(task.id, runner="mock", secrets=refs)
    assert exc.value.missing == ("FOO",)
    assert store.list_sessions() == []


def test_sqlite_session_gets_fixture_value_db_dump_clean(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv(ENV_KEY, FIXTURE_VALUE)
    db = _memory_db()
    try:
        project = db.scalar(select(Project).where(Project.slug == "default"))
        support = db.scalar(select(Agent).where(Agent.name == "support"))
        replace_agent_secrets(
            db,
            support,
            [SecretRefItem(name="FOO", provider="env", key=ENV_KEY)],
        )
        db.refresh(support)
        runtime = resolve_agent_secrets(support)
        assert runtime.get("FOO") == FIXTURE_VALUE

        task = DbTask(
            project_id=project.id,
            name="Front ticket",
            assignee_agent_id=support.id,
            status="todo",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        session = run_task_session(db, task, support)
        assert session.runtime_secrets.get("FOO") == FIXTURE_VALUE
        events = session.get_tool_events()
        details = " ".join(str(row.get("detail", "")) for row in events)
        assert "session.secrets" in str(events)
        assert FIXTURE_VALUE not in details
        assert FIXTURE_VALUE not in (session.summary or "")
        dump = _sqlite_dump(db)
        assert FIXTURE_VALUE not in dump
        assert ENV_KEY in dump
    finally:
        db.close()


def test_sqlite_unresolved_ref_denies_run(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.delenv(ENV_KEY, raising=False)
    db = _memory_db()
    try:
        project = db.scalar(select(Project).where(Project.slug == "default"))
        support = db.scalar(select(Agent).where(Agent.name == "support"))
        replace_agent_secrets(
            db,
            support,
            [SecretRefItem(name="FOO", provider="env", key=ENV_KEY)],
        )
        db.refresh(support)
        task = DbTask(
            project_id=project.id,
            name="Front ticket",
            assignee_agent_id=support.id,
            status="todo",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        with pytest.raises(UnresolvedSecretRefError, match="FOO"):
            run_task_session(db, task, support)
        dump = _sqlite_dump(db)
        assert FIXTURE_VALUE not in dump
    finally:
        db.close()
