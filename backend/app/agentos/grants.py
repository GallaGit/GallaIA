"""Per-agent capability grants. Default deny: missing grant → refuse.

Phase 2 Isolation — grants wall only (not network policy, filesystem ACL,
or secret-ref injection).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Literal

GrantKind = Literal["mcp", "repo", "env"]
GRANT_KINDS: tuple[GrantKind, ...] = ("mcp", "repo", "env")

# Runner / session plumbing — not agent MCP capabilities.
CONTROL_PLANE_PREFIXES = frozenset(
    {
        "kanban",
        "session",
        "openrouter",
        "anthropic",
        "claude",
        "prompt",
        "mock",
    }
)


def normalize_grant(kind: str, name: str) -> tuple[str, str]:
    """Canonical (kind, name). Env keys stay case-sensitive; MCP/repo are lowercased."""
    kind_n = kind.strip().lower()
    raw = name.strip()
    if kind_n == "env":
        return kind_n, raw
    return kind_n, raw.lower()


@dataclass(frozen=True)
class Grant:
    kind: GrantKind
    name: str

    def normalized(self) -> Grant:
        kind, name = normalize_grant(self.kind, self.name)
        if kind not in GRANT_KINDS:
            raise ValueError(f"Unknown grant kind {kind!r}")
        return Grant(kind=kind, name=name)  # type: ignore[arg-type]


@dataclass(frozen=True)
class ToolDecision:
    allowed: bool
    reason: str = ""
    kind: str | None = None
    name: str | None = None


@dataclass(frozen=True)
class GrantSet:
    """Explicit allow-list. Empty set denies every gated capability."""

    items: frozenset[tuple[str, str]] = frozenset()

    @classmethod
    def from_pairs(cls, pairs: Iterable[tuple[str, str]]) -> GrantSet:
        items: set[tuple[str, str]] = set()
        for kind, name in pairs:
            kind_n, name_n = normalize_grant(kind, name)
            if kind_n not in GRANT_KINDS:
                raise ValueError(f"Unknown grant kind {kind_n!r}")
            if name_n:
                items.add((kind_n, name_n))
        return cls(items=frozenset(items))

    def allows(self, kind: str, name: str) -> bool:
        key = normalize_grant(kind, name)
        if not key[1] or key[0] not in GRANT_KINDS:
            return False
        return key in self.items

    def as_list(self) -> list[dict[str, str]]:
        return sorted(
            [{"kind": k, "name": n} for k, n in self.items],
            key=lambda row: (row["kind"], row["name"]),
        )


def evaluate_tool(
    grants: GrantSet,
    tool_name: str,
    tool_input: dict[str, Any] | None = None,
) -> ToolDecision:
    """Default-deny a tool unless a matching grant exists (or it is control-plane)."""
    prefix = tool_name.split(".", 1)[0].strip().lower()
    if not prefix:
        return ToolDecision(allowed=False, reason="missing grant mcp:", kind="mcp", name="")
    if prefix in CONTROL_PLANE_PREFIXES:
        return ToolDecision(allowed=True)

    payload = tool_input or {}
    if prefix == "env":
        kind, name = "env", str(payload.get("key") or payload.get("name") or "")
    elif prefix == "repo":
        kind, name = "repo", str(payload.get("path") or payload.get("repo") or "")
    else:
        kind, name = "mcp", prefix

    kind_n, name_n = normalize_grant(kind, name)
    if grants.allows(kind_n, name_n):
        return ToolDecision(allowed=True, kind=kind_n, name=name_n)
    return ToolDecision(
        allowed=False,
        reason=f"missing grant {kind_n}:{name_n}",
        kind=kind_n,
        name=name_n,
    )


def gated_output(
    grants: GrantSet,
    tool_name: str,
    tool_input: dict[str, Any] | None,
    allowed_output: dict[str, Any],
) -> dict[str, Any]:
    """Return tool output, or a deny payload if the grant is missing."""
    decision = evaluate_tool(grants, tool_name, tool_input)
    if decision.allowed:
        return {"ok": True, **allowed_output}
    return {
        "ok": False,
        "denied": True,
        "reason": decision.reason,
        "missing_grant": {"kind": decision.kind, "name": decision.name},
    }
