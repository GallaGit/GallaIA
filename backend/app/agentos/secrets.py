"""Per-agent secret refs. Persist names/keys only; resolve at session start.

Phase 2 Isolation — secret-refs wall. Values live in process env (or a test
fixture), never in SQLite. Unresolved refs deny the session.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Iterable, Literal, Mapping

SecretProvider = Literal["env"]
SECRET_PROVIDERS: tuple[SecretProvider, ...] = ("env",)

# Env-style identifiers only. Tokens with hyphens/prefixes cannot sneak in as keys.
_REF_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")

_RAW_PREFIXES = (
    "sk-",
    "sk-ant-",
    "ghp_",
    "gho_",
    "ghu_",
    "ghs_",
    "github_pat_",
    "xoxb-",
    "xoxp-",
    "xoxa-",
    "xoxr-",
    "xoxe-",
    "AKIA",
    "ASIA",
    "eyJ",
)


class UnresolvedSecretRef(Exception):
    """Session start is denied when a persisted ref has no value in env/fixture."""

    def __init__(self, missing: tuple[str, ...]):
        self.missing = missing
        names = ", ".join(missing) if missing else "(unknown)"
        super().__init__(f"unresolved secret ref: {names}")


def looks_like_raw_secret(value: str) -> bool:
    """True when a string looks like a token/value rather than a ref name/key."""
    text = (value or "").strip()
    if not text:
        return False
    if any(ch.isspace() for ch in text) or "=" in text:
        return True
    for prefix in _RAW_PREFIXES:
        if text.startswith(prefix) or text.lower().startswith(prefix.lower()):
            return True
    if len(text) >= 40 and re.fullmatch(r"[A-Za-z0-9+/=_-]+", text):
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", text):
            return True
    return False


def normalize_provider(provider: str) -> SecretProvider:
    value = (provider or "env").strip().lower() or "env"
    if value not in SECRET_PROVIDERS:
        raise ValueError(f"Unknown secret provider {provider!r}")
    return value  # type: ignore[return-value]


def normalize_ref_ident(value: str, *, field: str) -> str:
    text = (value or "").strip()
    if not text:
        raise ValueError(f"{field} is required")
    if looks_like_raw_secret(text):
        raise ValueError(f"{field} looks like a raw secret; store a ref name/key only")
    if not _REF_IDENT.fullmatch(text):
        raise ValueError(
            f"{field} must be an identifier (letters, digits, underscore), not a secret value"
        )
    return text


@dataclass(frozen=True)
class SecretRef:
    """Pointer at env (or a local provider). Never holds the secret value."""

    name: str
    provider: SecretProvider = "env"
    key: str = ""

    def normalized(self) -> SecretRef:
        name = normalize_ref_ident(self.name, field="name")
        provider = normalize_provider(self.provider)
        key_raw = (self.key or "").strip() or name
        key = normalize_ref_ident(key_raw, field="key")
        return SecretRef(name=name, provider=provider, key=key)

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "provider": self.provider, "key": self.key}


@dataclass(frozen=True)
class SecretRefSet:
    """Named refs to inject at session start. Empty set injects nothing."""

    items: tuple[SecretRef, ...] = ()

    @classmethod
    def empty(cls) -> SecretRefSet:
        return cls(items=())

    @classmethod
    def from_items(cls, items: Iterable[SecretRef | dict[str, Any]]) -> SecretRefSet:
        seen: dict[str, SecretRef] = {}
        for item in items:
            ref = (
                SecretRef(
                    name=str(item.get("name") or ""),
                    provider=str(item.get("provider") or "env"),  # type: ignore[arg-type]
                    key=str(item.get("key") or ""),
                )
                if isinstance(item, dict)
                else item
            ).normalized()
            seen[ref.name] = ref
        ordered = tuple(sorted(seen.values(), key=lambda r: r.name))
        return cls(items=ordered)

    def as_list(self) -> list[dict[str, str]]:
        return [item.as_dict() for item in self.items]

    def names(self) -> list[str]:
        return [item.name for item in self.items]


@dataclass(frozen=True)
class SecretRuntime:
    """In-memory resolved secrets for one session. Do not persist values."""

    values: dict[str, str]
    refs: tuple[SecretRef, ...] = ()

    @classmethod
    def empty(cls) -> SecretRuntime:
        return cls(values={}, refs=())

    def get(self, name: str) -> str | None:
        return self.values.get(name)

    def as_public_dict(self) -> dict[str, Any]:
        """Safe for tool logs / API: names only, never values."""
        return {"injected": sorted(self.values), "count": len(self.values)}


def resolve_secret_refs(
    refs: SecretRefSet,
    *,
    environ: Mapping[str, str] | None = None,
    fixture: Mapping[str, str] | None = None,
) -> SecretRuntime:
    """Resolve refs from fixture then process env. Missing/empty → deny."""
    env_map = os.environ if environ is None else environ
    overlay = fixture or {}
    resolved: dict[str, str] = {}
    missing: list[str] = []
    for ref in refs.items:
        raw = overlay.get(ref.key)
        if raw is None:
            raw = env_map.get(ref.key)
        value = "" if raw is None else str(raw)
        if not value:
            missing.append(ref.name)
            continue
        resolved[ref.name] = value
    if missing:
        raise UnresolvedSecretRef(tuple(missing))
    return SecretRuntime(values=resolved, refs=refs.items)


def gated_secret_output(runtime: SecretRuntime, name: str) -> dict[str, Any]:
    """Presence check for a named secret. Never returns the value."""
    present = runtime.get(name) is not None
    if not present:
        return {
            "ok": False,
            "denied": True,
            "reason": f"unresolved secret ref: {name}",
            "secret": {"name": name},
        }
    return {"ok": True, "name": name, "present": True}
