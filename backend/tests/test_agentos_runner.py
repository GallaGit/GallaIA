"""Smoke tests for AgentOS seeds + mock runner (no Anthropic key required)."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `import app` when running from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agentos.models import Task
from app.agentos.runner import SessionRunner, resolve_runner
from app.agentos.seeds import AGENT_SEEDS, get_seed, list_seeds
from app.agentos.store import AgentOSStore


def test_three_seeds_labeled_reconstructed():
    names = {s.name for s in list_seeds()}
    assert names == {"default", "plan", "senior-dev"}
    for seed in AGENT_SEEDS.values():
        assert "not his verbatim" in seed.prompt_origin.lower() or "not his verbatim" in seed.role_prompt.lower()
        assert "Reconstructed" in seed.prompt_origin or "Reconstructed" in seed.role_prompt
        assert "Reconstructed" in seed.foundational_prompt


def test_mock_runner_advances_kanban_and_logs_tools(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    store = AgentOSStore()
    task = store.create_task(
        Task(name="Ship AgentOS MVP", description="seeds + runner", assignee_agent="plan")
    )
    result = SessionRunner(store).run(task.id)
    assert result.runner == "mock"
    assert result.used_anthropic is False
    assert result.task.status == "done"
    assert result.session.status == "destroyed"
    names = [e.name for e in result.tool_events]
    assert names.count("kanban.move") >= 3
    assert "session.destroy" in names
    assert get_seed("plan").name == "plan"


def test_resolve_runner_defaults_to_mock(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert resolve_runner(None) == "mock"
    assert resolve_runner("anthropic") == "mock"
