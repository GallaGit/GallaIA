"""Smoke tests for AgentOS seeds + mock runner (no LLM key required)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.error import HTTPError
from io import BytesIO

# Allow `import app` when running from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agentos.models import Task
from app.agentos.runner import SessionRunner, resolve_runner
from app.agentos.seeds import AGENT_SEEDS, get_seed, list_seeds
from app.agentos.store import AgentOSStore
from app.core.config import get_settings


def _clear_llm_env(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    get_settings.cache_clear()


def test_three_seeds_labeled_reconstructed():
    names = {s.name for s in list_seeds()}
    assert names == {"default", "plan", "senior-dev"}
    for seed in AGENT_SEEDS.values():
        assert "not his verbatim" in seed.prompt_origin.lower() or "not his verbatim" in seed.role_prompt.lower()
        assert "Reconstructed" in seed.prompt_origin or "Reconstructed" in seed.role_prompt
        assert "Reconstructed" in seed.foundational_prompt


def test_mock_runner_advances_kanban_and_logs_tools(monkeypatch):
    _clear_llm_env(monkeypatch)
    store = AgentOSStore()
    task = store.create_task(
        Task(name="Ship AgentOS MVP", description="seeds + runner", assignee_agent="plan")
    )
    result = SessionRunner(store).run(task.id, runner="mock")
    assert result.runner == "mock"
    assert result.used_anthropic is False
    assert result.used_openrouter is False
    assert result.task.status == "done"
    assert result.session.status == "destroyed"
    names = [e.name for e in result.tool_events]
    assert names.count("kanban.move") >= 3
    assert "session.destroy" in names
    assert get_seed("plan").name == "plan"


def test_resolve_runner_defaults_to_mock(monkeypatch):
    _clear_llm_env(monkeypatch)
    assert resolve_runner(None) == "mock"
    assert resolve_runner("anthropic") == "mock"
    assert resolve_runner("openrouter") == "mock"


def test_resolve_runner_openrouter_when_key_set(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    get_settings.cache_clear()
    assert resolve_runner(None) == "openrouter"
    assert resolve_runner("openrouter") == "openrouter"
    assert resolve_runner("anthropic") == "openrouter"
    assert resolve_runner("mock") == "mock"
    get_settings.cache_clear()


def test_openrouter_complete_parses_choices(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free")
    get_settings.cache_clear()

    class _FakeResp:
        def __init__(self, payload: dict):
            self._payload = json.dumps(payload).encode()

        def read(self):
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(req, timeout=None):  # noqa: ARG001
        return _FakeResp({"choices": [{"message": {"content": "Nemotron plan stub"}}]})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    from app.providers.openrouter import complete

    result = complete(system="sys", user="do the task")
    assert result.text == "Nemotron plan stub"
    assert result.model == "nvidia/nemotron-3-ultra-550b-a55b:free"
    get_settings.cache_clear()


def test_openrouter_runner_logs_tool_event(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    get_settings.cache_clear()

    class _FakeResp:
        def read(self):
            return json.dumps(
                {"choices": [{"message": {"content": "Done via Nemotron"}}]}
            ).encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: _FakeResp())

    store = AgentOSStore()
    task = store.create_task(Task(name="Try Nemotron", assignee_agent="default"))
    result = SessionRunner(store).run(task.id)
    assert result.runner == "openrouter"
    assert result.used_openrouter is True
    assert "Nemotron" in result.summary
    names = [e.name for e in result.tool_events]
    assert "openrouter.chat.completions" in names
    get_settings.cache_clear()


def test_openrouter_http_error_falls_back_to_mock(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    get_settings.cache_clear()

    def fake_urlopen(req, timeout=None):  # noqa: ARG001
        raise HTTPError(
            "https://openrouter.ai/api/v1/chat/completions",
            401,
            "Unauthorized",
            hdrs={},
            fp=BytesIO(b"bad key"),
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    store = AgentOSStore()
    task = store.create_task(Task(name="Bad key", assignee_agent="default"))
    result = SessionRunner(store).run(task.id, runner="openrouter")
    assert result.used_openrouter is False
    assert result.task.status == "done"
    names = [e.name for e in result.tool_events]
    assert "openrouter.error" in names
    get_settings.cache_clear()
