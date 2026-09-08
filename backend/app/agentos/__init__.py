"""AgentOS MVP — seeds + session runner (mock / optional Anthropic or OpenRouter).

Prompts and role contracts are reconstructed from Danny Postma's AgentOS talk
(via public blueprint gist) — not his verbatim files. Every seed prompt is
labeled accordingly.
"""

from app.agentos.seeds import AGENT_SEEDS, get_seed, list_seeds
from app.agentos.runner import SessionRunner, RunResult

__all__ = [
    "AGENT_SEEDS",
    "get_seed",
    "list_seeds",
    "SessionRunner",
    "RunResult",
]
