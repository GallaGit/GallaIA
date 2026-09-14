"""Per-agent network policy at the mock/runner proxy.

Phase 2 Isolation — network wall (`open` | `limited` + host allowlist).
`open` allows any host; `limited` allows only the host allowlist.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable, Literal
from urllib.parse import urlparse

NetworkMode = Literal["open", "limited"]
NETWORK_MODES: tuple[NetworkMode, ...] = ("open", "limited")
HTTP_TOOLS = frozenset({"http.fetch", "http.request", "http.get", "fetch"})


def normalize_mode(mode: str) -> NetworkMode:
    value = (mode or "").strip().lower()
    if value not in NETWORK_MODES:
        raise ValueError(f"Unknown network mode {mode!r}")
    return value  # type: ignore[return-value]


def extract_host(url_or_host: str) -> str:
    """Hostname from a URL or bare host; lowercased, no trailing dot."""
    raw = (url_or_host or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urlparse(raw)
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    return host


def normalize_allowlist(hosts: Iterable[str]) -> tuple[str, ...]:
    seen: list[str] = []
    found: set[str] = set()
    for item in hosts:
        host = extract_host(str(item))
        if not host or host in found:
            continue
        found.add(host)
        seen.append(host)
    return tuple(seen)


@dataclass(frozen=True)
class HostDecision:
    allowed: bool
    reason: str = ""
    mode: NetworkMode = "open"
    host: str = ""


@dataclass(frozen=True)
class NetworkPolicy:
    """Runner-proxy policy. Missing/empty row defaults to open."""

    mode: NetworkMode = "open"
    allowlist: tuple[str, ...] = ()

    @classmethod
    def open(cls) -> NetworkPolicy:
        return cls(mode="open", allowlist=())

    @classmethod
    def limited(cls, hosts: Iterable[str]) -> NetworkPolicy:
        return cls(mode="limited", allowlist=normalize_allowlist(hosts))

    @classmethod
    def from_parts(cls, mode: str, hosts: Iterable[str]) -> NetworkPolicy:
        resolved = normalize_mode(mode)
        if resolved == "open":
            return cls(mode="open", allowlist=normalize_allowlist(hosts))
        return cls.limited(hosts)

    def allows_host(self, url_or_host: str) -> bool:
        if self.mode == "open":
            return True
        host = extract_host(url_or_host)
        if not host:
            return False
        return host in self.allowlist

    def as_dict(self) -> dict[str, Any]:
        return {"mode": self.mode, "allowlist": list(self.allowlist)}


def evaluate_http(policy: NetworkPolicy, url_or_host: str) -> HostDecision:
    host = extract_host(url_or_host)
    if policy.mode == "open":
        return HostDecision(allowed=True, mode="open", host=host)
    if not host:
        return HostDecision(
            allowed=False,
            reason="limited network: missing host",
            mode="limited",
            host="",
        )
    if host in policy.allowlist:
        return HostDecision(allowed=True, mode="limited", host=host)
    return HostDecision(
        allowed=False,
        reason=f"limited network: host not allowlisted: {host}",
        mode="limited",
        host=host,
    )


def gated_http_output(
    policy: NetworkPolicy,
    url_or_host: str,
    allowed_output: dict[str, Any],
) -> dict[str, Any]:
    """Return fetch output, or a deny payload when limited + host not listed."""
    decision = evaluate_http(policy, url_or_host)
    if decision.allowed:
        return {"ok": True, **allowed_output}
    return {
        "ok": False,
        "denied": True,
        "reason": decision.reason,
        "network": {
            "mode": decision.mode,
            "host": decision.host,
            "allowlist": list(policy.allowlist),
        },
    }


def parse_allowlist_json(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return ()
    if not isinstance(data, list):
        return ()
    return normalize_allowlist(str(item) for item in data)


def dump_allowlist_json(hosts: Iterable[str]) -> str:
    return json.dumps(list(normalize_allowlist(hosts)))
