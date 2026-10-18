"""F2.1b — runner via gateway, per-agent model, usage log, optional litellm.

All tests use fake transports / a fake `litellm` module: no network.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agentos.models import Task as MemTask
from app.agentos.runner import SessionRunner, resolve_runner
from app.agentos.store import AgentOSStore
from app.core.config import DEFAULT_OPENROUTER_MODEL, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.llm import gateway
from app.llm.gateway import LLMError, ProviderConfig, UsageRecord
from app.llm.usage import db_usage_sink, usage_summary
from app.main import app
from app.models import Agent, LLMUsage, Project, Thread
from app.models.task import Task as DbTask
from app.schemas.agentos_yml import AgentYml
from app.services.runner import run_task_session
from app.services.seed import ensure_seed_agents_and_grants, seed_if_empty
from app.services.thread_agents import GatewayLLM, advance_thread, default_llm

OR_KEY = "or-secret-test-key"
GQ_KEY = "gq-secret-test-key"
OR = ProviderConfig("openrouter", OR_KEY, "vendor/default:free", "https://openrouter.ai/api/v1")
GQ = ProviderConfig("groq", GQ_KEY, "llama-3.3-70b-versatile", "https://api.groq.com/openai/v1")


def _reply(text, usage=None):
    data = {"choices": [{"message": {"role": "assistant", "content": text}}]}
    if usage is not None:
        data["usage"] = usage
    return data


def _transport(handlers):
    calls: list[dict] = []

    def _send(url, headers, payload, timeout):  # noqa: ARG001
        calls.append({"url": url, "payload": payload, "headers": dict(headers)})
        name = "openrouter" if "openrouter" in url else "groq"
        handler = handlers[name]
        if isinstance(handler, Exception):
            raise handler
        return handler(payload) if callable(handler) else handler

    return _send, calls


def _memory_db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_conn, _record):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    seed_if_empty(db)
    ensure_seed_agents_and_grants(db)
    return db


def _use_fake_providers(monkeypatch, handlers, providers=(OR, GQ)):
    """Route the real gateway (no explicit transport) to a fake HTTP layer."""
    send, calls = _transport(handlers)
    monkeypatch.setattr(gateway, "configured_providers", lambda: list(providers))
    monkeypatch.setattr(gateway, "_urllib_transport", send)
    return calls


# --- model selection --------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, (None, None)),
        ("", (None, None)),
        ("inherit", (None, None)),
        ("claude-sonnet-4", (None, None)),
        ("claude-opus-4", (None, None)),
        ("mock", ("mock", None)),
        ("groq/llama-3.1-8b-instant", ("groq", "llama-3.1-8b-instant")),
        ("openrouter/meta/llama:free", ("openrouter", "meta/llama:free")),
        ("nvidia/nemotron:free", ("openrouter", "nvidia/nemotron:free")),
        ("anthropic/claude-sonnet-4", ("openrouter", "anthropic/claude-sonnet-4")),
    ],
)
def test_resolve_model(value, expected):
    assert gateway.resolve_model(value) == expected


def test_providers_for_model_overrides_and_orders():
    assert gateway.providers_for_model(None, [OR, GQ]) == [OR, GQ]
    assert gateway.providers_for_model("claude-sonnet-4", [OR, GQ]) == [OR, GQ]
    assert gateway.providers_for_model("mock", [OR, GQ]) == []

    chain = gateway.providers_for_model("x/agent-model", [OR, GQ])
    assert [(p.name, p.model) for p in chain] == [
        ("openrouter", "x/agent-model"),
        ("groq", GQ.model),
    ]

    chain = gateway.providers_for_model("groq/llama-3.1-8b-instant", [OR, GQ])
    assert [(p.name, p.model) for p in chain] == [
        ("groq", "llama-3.1-8b-instant"),
        ("openrouter", OR.model),
    ]


def test_complete_sends_agent_model():
    send, calls = _transport({"openrouter": _reply("ok")})
    result = gateway.complete("s", "u", model="x/agent-model", providers=[OR], transport=send)
    assert calls[0]["payload"]["model"] == "x/agent-model"
    assert result.model == "openrouter/x/agent-model"


def test_mock_model_skips_providers():
    send, calls = _transport({})
    result = gateway.complete(
        "s", "u", model="mock", providers=[OR, GQ], transport=send, fallback=lambda s, u: "m"
    )
    assert result.provider == "mock" and result.text == "m" and calls == []


# --- usage ------------------------------------------------------------------


def test_usage_tokens_latency_cost_and_attempts():
    send, _ = _transport(
        {
            "openrouter": LLMError(f"HTTP 401: bad key {OR_KEY}"),
            "groq": _reply("hola", {"prompt_tokens": 12, "completion_tokens": 7}),
        }
    )
    records: list[UsageRecord] = []
    result = gateway.complete("s", "u", providers=[OR, GQ], transport=send, on_usage=records.append)

    assert result.provider == "groq"
    assert (result.input_tokens, result.output_tokens) == (12, 7)
    assert result.latency_ms is not None and result.latency_ms >= 0
    assert result.cost_usd is None  # Groq pricing is not trivial
    assert [(r.provider, r.ok) for r in records] == [("openrouter", False), ("groq", True)]
    assert result.attempts == tuple(records)
    assert OR_KEY not in (records[0].error or "")
    assert "***" in records[0].error


def test_free_model_costs_zero_and_missing_usage_is_none():
    send, _ = _transport({"openrouter": _reply("ok")})
    result = gateway.complete("s", "u", providers=[OR], transport=send)
    assert result.cost_usd == 0.0
    assert result.input_tokens is None and result.output_tokens is None


def test_mock_fallback_is_recorded():
    records: list[UsageRecord] = []
    result = gateway.complete("s", "u", providers=[], fallback=lambda s, u: "m", on_usage=records.append)
    assert result.provider == "mock"
    assert [(r.provider, r.cost_usd) for r in records] == [("mock", 0.0)]


def test_broken_usage_sink_never_breaks_the_call():
    send, _ = _transport({"openrouter": _reply("ok")})

    def boom(_record):
        raise RuntimeError("sink down")

    result = gateway.complete("s", "u", providers=[OR], transport=send, on_usage=boom)
    assert result.text == "ok"


def test_db_sink_and_usage_endpoint():
    db = _memory_db()
    try:
        send, _ = _transport(
            {
                "openrouter": LLMError("HTTP 500"),
                "groq": _reply("ok", {"prompt_tokens": 3, "completion_tokens": 2}),
            }
        )
        gateway.complete(
            "s", "u", providers=[OR, GQ], transport=send,
            on_usage=db_usage_sink(db, source="thread", agent="fe", thread_id=9),
        )
        db.commit()
        rows = list(db.scalars(select(LLMUsage).order_by(LLMUsage.id)).all())
        assert [(r.provider, r.ok, r.agent, r.source, r.thread_id) for r in rows] == [
            ("openrouter", False, "fe", "thread", 9),
            ("groq", True, "fe", "thread", 9),
        ]
        summary = {s["provider"]: s for s in usage_summary(db)}
        assert summary["groq"]["input_tokens"] == 3
        assert summary["openrouter"]["ok_calls"] == 0

        def _override():
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            body = TestClient(app).get("/api/v1/llm/usage", params={"limit": 5}).json()
        finally:
            app.dependency_overrides.clear()
        assert body["backend"] == "http"
        assert [r["provider"] for r in body["recent"]] == ["groq", "openrouter"]
        assert "prompt" not in body["recent"][0]
        assert OR_KEY not in str(body) and GQ_KEY not in str(body)
    finally:
        db.close()


# --- session runner (services/runner.py) ------------------------------------


def _db_task(db, agent_name="fe", model=None):
    project = db.scalar(select(Project).where(Project.slug == "default"))
    agent = db.scalar(select(Agent).where(Agent.name == agent_name))
    if model is not None:
        agent.model = model
    task = DbTask(project_id=project.id, name="Ticket F2.1b", assignee_agent_id=agent.id, status="todo")
    db.add(task)
    db.commit()
    db.refresh(task)
    return task, agent


def test_task_session_uses_gateway_with_agent_model(monkeypatch):
    calls = _use_fake_providers(
        monkeypatch,
        {"openrouter": _reply("resumen LLM", {"prompt_tokens": 50, "completion_tokens": 9}), "groq": _reply("no")},
    )
    db = _memory_db()
    try:
        task, agent = _db_task(db, model="vendor/fe-model:free")
        session = run_task_session(db, task, agent)

        assert session.runner == "openrouter"
        assert session.summary == "resumen LLM"
        assert [c["payload"]["model"] for c in calls] == ["vendor/fe-model:free"]
        tools = [e["tool"] for e in session.get_tool_events()]
        assert "openrouter.chat.completions" in tools
        rows = list(db.scalars(select(LLMUsage)).all())
        assert len(rows) == 1
        row = rows[0]
        assert (row.source, row.agent, row.session_id) == ("session", "fe", session.id)
        assert (row.input_tokens, row.output_tokens, row.cost_usd) == (50, 9, 0.0)
        assert row.model == "openrouter/vendor/fe-model:free"
    finally:
        db.close()


def test_task_session_legacy_claude_model_uses_default(monkeypatch):
    calls = _use_fake_providers(monkeypatch, {"openrouter": _reply("ok"), "groq": _reply("no")})
    db = _memory_db()
    try:
        task, agent = _db_task(db, model="claude-sonnet-4")
        run_task_session(db, task, agent)
        assert calls[0]["payload"]["model"] == OR.model
    finally:
        db.close()


def test_task_session_falls_back_to_groq_then_mock(monkeypatch):
    calls = _use_fake_providers(
        monkeypatch, {"openrouter": LLMError("HTTP 429"), "groq": LLMError("HTTP 503")}
    )
    db = _memory_db()
    try:
        task, agent = _db_task(db)
        session = run_task_session(db, task, agent)
        assert len(calls) == 2
        assert session.runner == "mock"
        assert session.summary.startswith("[mock]")
        tools = [e["tool"] for e in session.get_tool_events()]
        assert {"openrouter.error", "groq.error", "llm.fallback"} <= set(tools)
        providers = [r.provider for r in db.scalars(select(LLMUsage).order_by(LLMUsage.id))]
        assert providers == ["openrouter", "groq", "mock"]
        assert task.status in ("done", "review")
    finally:
        db.close()


def test_task_session_groq_only(monkeypatch):
    _use_fake_providers(monkeypatch, {"groq": _reply("desde groq")}, providers=(GQ,))
    db = _memory_db()
    try:
        task, agent = _db_task(db)
        session = run_task_session(db, task, agent)
        assert session.runner == "groq"
        assert session.summary == "desde groq"
    finally:
        db.close()


def test_task_session_without_keys_stays_mock():
    db = _memory_db()
    try:
        task, agent = _db_task(db)
        session = run_task_session(db, task, agent)
        assert session.runner == "mock"
        assert db.scalars(select(LLMUsage)).first() is None
    finally:
        db.close()


# --- in-memory AgentOS runner -------------------------------------------------


def test_agentos_runner_groq_only(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", GQ_KEY)
    get_settings.cache_clear()
    assert resolve_runner(None) == "groq"
    send, calls = _transport({"groq": _reply("groq listo")})
    monkeypatch.setattr(gateway, "_urllib_transport", send)

    store = AgentOSStore()
    task = store.create_task(MemTask(name="Groq", assignee_agent="orquestador"))
    result = SessionRunner(store).run(task.id)

    assert result.runner == "groq"
    assert result.summary == "groq listo"
    assert result.used_openrouter is False
    assert "groq.chat.completions" in [e.name for e in result.tool_events]
    assert calls[0]["headers"]["Authorization"] == f"Bearer {GQ_KEY}"


# --- thread agents ----------------------------------------------------------


def test_thread_agents_use_per_agent_model_and_log_usage(monkeypatch):
    def _handler(payload):
        return _reply(f"respuesta {payload['model']}", {"prompt_tokens": 1, "completion_tokens": 1})

    calls = _use_fake_providers(monkeypatch, {"openrouter": _handler, "groq": _handler}, providers=(OR,))
    db = _memory_db()
    try:
        fe = db.scalar(select(Agent).where(Agent.name == "fe"))
        fe.model = "vendor/fe-model:free"
        be = db.scalar(select(Agent).where(Agent.name == "be"))
        be.model = "claude-sonnet-4"  # legacy row -> default model
        project = db.scalar(select(Project).where(Project.slug == "default"))
        thread = Thread(title="F2.1b", created_by="user", project_id=project.id)
        db.add(thread)
        db.commit()
        from app.models import Message

        db.add(Message(thread_id=thread.id, sender="user", recipient="orquestador", kind="text", body="Haz X"))
        db.commit()

        llm = default_llm(db, thread.id, project.id)
        assert isinstance(llm, GatewayLLM)
        created = advance_thread(db, thread, max_steps=6)

        models = [c["payload"]["model"] for c in calls]
        assert "vendor/fe-model:free" in models
        assert OR.model in models  # orquestador (seed default) + legacy BE
        results = {m.sender: m.body for m in created if m.kind == "result"}
        assert results["fe"] == "respuesta vendor/fe-model:free"
        rows = list(db.scalars(select(LLMUsage)).all())
        assert len(rows) == len(calls)
        assert {r.agent for r in rows} == {"orquestador", "fe", "be"}
        assert all(r.source == "thread" and r.thread_id == thread.id for r in rows)
    finally:
        db.close()


# --- defaults -----------------------------------------------------------------


def test_new_agent_defaults_use_openrouter_model():
    from app.cli import _build_parser

    assert AgentYml(name="x", title="x").model == DEFAULT_OPENROUTER_MODEL
    assert Agent.__table__.c.model.default.arg == DEFAULT_OPENROUTER_MODEL
    args = _build_parser().parse_args(["create-agent", "--name", "x"])
    assert args.model == DEFAULT_OPENROUTER_MODEL


# --- optional litellm backend ---------------------------------------------------


def _fake_litellm(monkeypatch, response=None, error=None):
    captured: dict = {}

    def completion(**kwargs):
        captured.update(kwargs)
        if error is not None:
            raise error
        return response

    module = types.ModuleType("litellm")
    module.completion = completion
    monkeypatch.setitem(sys.modules, "litellm", module)
    return captured


def test_litellm_backend_when_enabled(monkeypatch):
    monkeypatch.setenv("GALLAIA_LLM_BACKEND", "litellm")
    get_settings.cache_clear()
    assert gateway.llm_backend() == "litellm"

    class _Resp:  # mimics litellm.ModelResponse.model_dump()
        def model_dump(self):
            return _reply("via litellm", {"prompt_tokens": 4, "completion_tokens": 5})

    captured = _fake_litellm(monkeypatch, response=_Resp())
    records: list[UsageRecord] = []
    result = gateway.complete("s", "u", model="x/m:free", providers=[OR], on_usage=records.append)

    assert result.text == "via litellm"
    assert (result.input_tokens, result.output_tokens) == (4, 5)
    assert captured["model"] == "openrouter/x/m:free"
    assert captured["api_base"] == OR.base_url
    assert captured["api_key"] == OR_KEY
    assert captured["extra_headers"]["X-Title"] == "GallaAI AgentOS"
    assert records[0].backend == "litellm"


def test_litellm_error_falls_back_and_redacts_key(monkeypatch):
    monkeypatch.setenv("GALLAIA_LLM_BACKEND", "litellm")
    get_settings.cache_clear()
    _fake_litellm(monkeypatch, error=RuntimeError(f"auth failed for {OR_KEY}"))
    records: list[UsageRecord] = []
    result = gateway.complete("s", "u", providers=[OR], fallback=lambda s, u: "m", on_usage=records.append)
    assert result.provider == "mock"
    assert OR_KEY not in (records[0].error or "")


def test_litellm_missing_uses_http(monkeypatch):
    monkeypatch.setenv("GALLAIA_LLM_BACKEND", "litellm")
    get_settings.cache_clear()
    monkeypatch.setitem(sys.modules, "litellm", None)  # import -> ImportError
    send, calls = _transport({"openrouter": _reply("via http")})
    monkeypatch.setattr(gateway, "_urllib_transport", send)
    result = gateway.complete("s", "u", providers=[OR])
    assert result.text == "via http"
    assert len(calls) == 1


def test_backend_defaults_to_http(monkeypatch):
    monkeypatch.delenv("GALLAIA_LLM_BACKEND", raising=False)
    get_settings.cache_clear()
    assert gateway.llm_backend() == "http"
    monkeypatch.setenv("GALLAIA_LLM_BACKEND", "nonsense")
    get_settings.cache_clear()
    assert gateway.llm_backend() == "http"
