"""Shared test setup: never reach a real LLM provider.

A developer `.env` may hold real OPENROUTER/GROQ keys; process env wins over
`.env` in pydantic-settings, so blank them for every test. Tests that need a
key set it themselves with monkeypatch (after this fixture runs).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402


@pytest.fixture(autouse=True)
def _no_real_llm_keys(monkeypatch):
    for var in ("OPENROUTER_API_KEY", "GROQ_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.setenv(var, "")
    monkeypatch.setenv("GALLAIA_LLM_BACKEND", "http")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _memory_checkpoints(monkeypatch):
    """F2.2b: never write ./data/checkpoints.db from tests; reset the runtime."""
    monkeypatch.setenv("GALLAIA_CHECKPOINT_DB", "memory")
    get_settings.cache_clear()
    try:
        from app.runtime import thread_graph
    except Exception:  # noqa: BLE001 — runtime importable without langgraph
        thread_graph = None  # type: ignore[assignment]
    if thread_graph is not None and thread_graph.langgraph_available():
        thread_graph.reset_runtime()
    yield
    if thread_graph is not None and thread_graph.langgraph_available():
        thread_graph.reset_runtime()
    get_settings.cache_clear()
