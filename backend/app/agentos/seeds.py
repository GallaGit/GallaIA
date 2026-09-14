"""Agent seed catalog for AgentOS MVP.

# Reconstructed from Danny Postma's AgentOS talk — not his verbatim prompt.
Source blueprint (also reconstructed, not verbatim):
https://gist.github.com/iannuttall/8152098b5ce8e6c1a7499ee561ed93f4
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.agentos.filesystem import FilesystemAcl, FsRoot
from app.agentos.grants import GrantSet
from app.agentos.network import NetworkPolicy
from app.agentos.secrets import SecretRefSet

PROMPT_ORIGIN = (
    "Reconstructed from Danny Postma's AgentOS talk — not his verbatim prompt."
)

# Shared foundational prompt (reconstructed, not verbatim).
FOUNDATIONAL_PROMPT = """\
# Reconstructed from Danny Postma's AgentOS talk — not his verbatim prompt.

You are running inside AgentOS (GallaIA).

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
    """One AgentOS role seed."""

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
    "default": AgentSeed(
        name="default",
        title="Default agent",
        model="claude-sonnet-4-5",
        foundational_prompt=FOUNDATIONAL_PROMPT,
        role_prompt="""\
# Reconstructed from Danny Postma's AgentOS talk — not his verbatim prompt.

You are the default AgentOS agent. Do the assigned task with the tools
you have. Finish or inbox if stuck.
""",
        one_job="General workhorse",
        mcp=("agentos", "inbox"),
        grants=(("mcp", "agentos"), ("mcp", "inbox")),
    ),
    "plan": AgentSeed(
        name="plan",
        title="Plan agent",
        model="claude-sonnet-4-5",
        foundational_prompt=FOUNDATIONAL_PROMPT,
        role_prompt="""\
# Reconstructed from Danny Postma's AgentOS talk — not his verbatim prompt.

You are a plan agent. You have one job: turn an approved specification
into a concrete, ordered implementation plan. Write the plan onto the
task (and as a file attachment). Then finish the task. You do not
implement. You do not open unrelated tools.
""",
        one_job="Turn an approved spec into a concrete implementation plan",
        skills=("plan-mode",),
        mcp=("agentos", "inbox"),
        grants=(("mcp", "agentos"), ("mcp", "inbox")),
        runner_preference="anthropic",
    ),
    "senior-dev": AgentSeed(
        name="senior-dev",
        title="Senior developer",
        model="claude-sonnet-4-5",
        foundational_prompt=FOUNDATIONAL_PROMPT,
        role_prompt="""\
# Reconstructed from Danny Postma's AgentOS talk — not his verbatim prompt.

You are a senior developer. Implement the assigned work, or apply review
fixes, in the granted repo. Follow the plan if one is attached. Commit
when done. Run available tests. Inbox the human only if you are blocked.
""",
        one_job="Implement / apply review fixes",
        mcp=("agentos", "inbox", "github"),
        grants=(("mcp", "agentos"), ("mcp", "inbox"), ("mcp", "github")),
        runner_preference="mock",
    ),
    "support": AgentSeed(
        name="support",
        title="Customer support",
        model="claude-sonnet-4-5",
        foundational_prompt=FOUNDATIONAL_PROMPT,
        role_prompt="""\
# Reconstructed from Danny Postma's AgentOS talk — not his verbatim prompt.

You are a customer support agent. You have one job: handle inbound
support via the Front MCP. You do not have GitHub. You do not have
repo access. You do not have Gmail. Finish or inbox if stuck.
""",
        one_job="Inbound support via Front MCP — no GitHub, no repo; limited network",
        mcp=("front",),
        grants=(("mcp", "front"),),
        network_mode="limited",
        network_allowlist=("api.front.com",),
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
