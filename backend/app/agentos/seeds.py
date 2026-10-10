"""Agent seed catalog for GallaIA v2 (F0).

Three personal software teammates: Orquestador, FE, BE.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.agentos.filesystem import FilesystemAcl, FsRoot
from app.agentos.grants import GrantSet
from app.agentos.network import NetworkPolicy
from app.agentos.secrets import SecretRefSet

PROMPT_ORIGIN = "GallaIA v2 seed — Orquestador / FE / BE."

# Shared foundational prompt for the personal agentic stack.
FOUNDATIONAL_PROMPT = """\
# GallaIA v2 — foundational prompt

You are running inside GallaIA, a personal agentic tool for building software.

You have only the tools, MCPs, repos, environment variables, and filesystem
folders listed in your session manifest. If a tool is not listed, you cannot
use it and you must not try to. Do not ask for more access.

The session container is ephemeral and will be destroyed when you finish.
Persist work by committing to a granted repo (if you have git-write) or by
writing through the filesystem MCP. Do not assume local disk survives.

When you need a human decision or you are stuck, use the Inbox MCP.
Do not message the human for routine progress. Write notable progress to
the task activity log.

Your job is the role prompt below. Do that job, then finish. Use the
AgentOS MCP to update the task. If this task has an approval gate, you
must NOT mark it done — leave it in review and inbox the human.

You may spawn a collaborator only if they appear on your collaboration list.
Least privilege is a safety rule, not a suggestion.
"""

KanbanStatus = Literal["todo", "doing", "review", "done"]


@dataclass(frozen=True)
class AgentSeed:
    """One GallaIA v2 role seed."""

    name: str
    title: str
    model: str
    foundational_prompt: str
    role_prompt: str
    prompt_origin: str = PROMPT_ORIGIN
    skills: tuple[str, ...] = ()
    mcp: tuple[str, ...] = ("agentos", "inbox")
    grants: tuple[tuple[str, str], ...] = (("mcp", "agentos"), ("mcp", "inbox"))
    network_mode: Literal["open", "limited"] = "open"
    network_allowlist: tuple[str, ...] = ()
    fs_roots: tuple[FsRoot, ...] | None = None
    secret_refs: tuple[tuple[str, str, str], ...] = ()
    runner_preference: Literal["mock", "anthropic", "openrouter", "inherit"] = "inherit"
    collaboration: tuple[str, ...] = ()
    one_job: str = ""

    def grant_set(self) -> GrantSet:
        return GrantSet.from_pairs(self.grants)

    def network_policy(self) -> NetworkPolicy:
        return NetworkPolicy.from_parts(self.network_mode, self.network_allowlist)

    def filesystem_acl(self) -> FilesystemAcl:
        if self.fs_roots is not None:
            return FilesystemAcl.from_roots(self.fs_roots)
        return FilesystemAcl.for_agent(self.name)

    def secret_ref_set(self) -> SecretRefSet:
        return SecretRefSet.from_items(
            {"name": name, "provider": provider, "key": key}
            for name, provider, key in self.secret_refs
        )


AGENT_SEEDS: dict[str, AgentSeed] = {
    "orquestador": AgentSeed(
        name="orquestador",
        title="Orquestador",
        model="claude-sonnet-4-5",
        foundational_prompt=FOUNDATIONAL_PROMPT,
        role_prompt="""\
# GallaIA v2 — Orquestador

You talk to Ociel. You plan work, split it into tasks, assign FE and BE,
review their output, and integrate results. You do not implement UI or API
yourself unless asked. Prefer clear briefs and approval gates when the human
must decide.
""",
        one_job="Hablar con Ociel, planificar, delegar a FE/BE, revisar e integrar",
        skills=("plan-mode",),
        mcp=("agentos", "inbox"),
        grants=(("mcp", "agentos"), ("mcp", "inbox")),
        collaboration=("fe", "be"),
        runner_preference="anthropic",
    ),
    "fe": AgentSeed(
        name="fe",
        title="FE",
        model="claude-sonnet-4-5",
        foundational_prompt=FOUNDATIONAL_PROMPT,
        role_prompt="""\
# GallaIA v2 — FE

You own React, TypeScript, Vite, and UI. Implement frontend tasks from the
Orquestador brief. Do not change FastAPI/backend unless the brief says so.
Run available frontend checks when granted. Inbox if blocked.
""",
        one_job="React / TypeScript / UI",
        mcp=("agentos", "inbox"),
        grants=(("mcp", "agentos"), ("mcp", "inbox")),
        network_mode="limited",
        network_allowlist=("registry.npmjs.org",),
        collaboration=("orquestador",),
        runner_preference="mock",
    ),
    "be": AgentSeed(
        name="be",
        title="BE",
        model="claude-sonnet-4-5",
        foundational_prompt=FOUNDATIONAL_PROMPT,
        role_prompt="""\
# GallaIA v2 — BE

You own FastAPI, API design, and data. Implement backend tasks from the
Orquestador brief. Do not change React/UI unless the brief says so.
Run available backend tests when granted. Inbox if blocked.
""",
        one_job="FastAPI / API / datos",
        mcp=("agentos", "inbox", "github"),
        grants=(("mcp", "agentos"), ("mcp", "inbox"), ("mcp", "github")),
        collaboration=("orquestador",),
        runner_preference="mock",
    ),
}


def list_seeds() -> list[AgentSeed]:
    return list(AGENT_SEEDS.values())


def get_seed(name: str) -> AgentSeed:
    try:
        return AGENT_SEEDS[name]
    except KeyError as exc:
        known = ", ".join(sorted(AGENT_SEEDS))
        raise KeyError(f"Unknown agent seed {name!r}. Known: {known}") from exc
