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
