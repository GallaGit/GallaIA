"""Per-agent filesystem MCP ACLs. Default deny outside allowed roots.

Phase 2 Isolation — filesystem wall only (not secret refs).
Read / write / delete are independent; writing does not imply delete.
Any `../` path component is denied (no silent resolve).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Literal

FsOp = Literal["read", "write", "delete"]
FS_OPS: tuple[FsOp, ...] = ("read", "write", "delete")
FS_TOOLS = frozenset({"fs.read", "fs.write", "fs.delete", "fs.list", "fs.mkdir"})


def agent_folder(name: str) -> str:
    slug = (name or "").strip().strip("/")
    if not slug:
        raise ValueError("agent folder name is empty")
    return f"/agents/{slug}"


def _raw_parts(path: str) -> list[str]:
    text = (path or "").replace("\\", "/").strip()
    return [p for p in text.split("/") if p not in ("", ".")]


def has_traversal(path: str) -> bool:
    """True when any path component is `..` (backslash treated as slash)."""
    if "\x00" in (path or ""):
        return True
    return any(part == ".." for part in _raw_parts(path))


def normalize_fs_path(path: str) -> str:
    """Absolute POSIX path. Does not resolve `..`; callers must deny traversal first."""
    text = (path or "").replace("\\", "/").strip()
    if not text or text == ".":
        return "/"
    parts = [p for p in text.split("/") if p not in ("", ".")]
    if not parts:
        return "/"
    return "/" + "/".join(parts)


def normalize_root(root: str) -> str:
    if has_traversal(root):
        raise ValueError(f"filesystem root must not contain '..': {root!r}")
    if "\x00" in (root or ""):
        raise ValueError("filesystem root must not contain NUL")
    normalized = normalize_fs_path(root)
    if normalized == "/":
        raise ValueError("filesystem root must not be '/' (too broad)")
    return normalized


def path_under_root(path: str, root: str) -> bool:
    """True if `path` is `root` or a descendant (slash-boundary, not string prefix)."""
    if path == root:
        return True
    return path.startswith(root + "/")


@dataclass(frozen=True)
class FsRoot:
    root: str
    can_read: bool = True
    can_write: bool = False
    can_delete: bool = False

    def normalized(self) -> FsRoot:
        return FsRoot(
            root=normalize_root(self.root),
            can_read=bool(self.can_read),
            can_write=bool(self.can_write),
            can_delete=bool(self.can_delete),
        )

    def allows(self, op: FsOp) -> bool:
        if op == "read":
            return self.can_read
        if op == "write":
            return self.can_write
        return self.can_delete

    def as_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "can_read": self.can_read,
            "can_write": self.can_write,
            "can_delete": self.can_delete,
        }


@dataclass(frozen=True)
class FsDecision:
    allowed: bool
    reason: str = ""
    op: FsOp | None = None
    path: str = ""
    traversal: bool = False
    root: str | None = None


@dataclass(frozen=True)
class FilesystemAcl:
    """Explicit roots. Empty ACL denies every path (default deny)."""

    roots: tuple[FsRoot, ...] = ()

    @classmethod
    def empty(cls) -> FilesystemAcl:
        return cls(roots=())

    @classmethod
    def for_agent(cls, name: str, *, write: bool = True, delete: bool = True) -> FilesystemAcl:
        return cls.from_roots(
            (FsRoot(agent_folder(name), can_read=True, can_write=write, can_delete=delete),)
        )

    @classmethod
    def from_roots(cls, roots: Iterable[FsRoot | dict[str, Any]]) -> FilesystemAcl:
        seen: dict[str, FsRoot] = {}
        for item in roots:
            root = (
                FsRoot(
                    root=str(item["root"]),
                    can_read=bool(item.get("can_read", True)),
                    can_write=bool(item.get("can_write", False)),
                    can_delete=bool(item.get("can_delete", False)),
                )
                if isinstance(item, dict)
                else item
            ).normalized()
            seen[root.root] = root
        ordered = tuple(sorted(seen.values(), key=lambda r: r.root))
        return cls(roots=ordered)

    def as_list(self) -> list[dict[str, Any]]:
        return [r.as_dict() for r in self.roots]

    def matching_root(self, path: str) -> FsRoot | None:
        matches = [r for r in self.roots if path_under_root(path, r.root)]
        if not matches:
            return None
        return max(matches, key=lambda r: len(r.root))


def evaluate_fs(acl: FilesystemAcl, op: str, path: str) -> FsDecision:
    if op not in FS_OPS:
        return FsDecision(allowed=False, reason=f"unknown fs op {op!r}", op=None, path=path)
    if not (path or "").strip() or "\x00" in path:
        return FsDecision(
            allowed=False,
            reason="fs: empty or invalid path",
            op=op,
            path=path or "",
        )
    if has_traversal(path):
        return FsDecision(
            allowed=False,
            reason="fs: path traversal denied",
            op=op,
            path=path,
            traversal=True,
        )
    normalized = normalize_fs_path(path)
    if normalized == "/":
        return FsDecision(
            allowed=False,
            reason="fs: path outside allowed roots",
            op=op,
            path=normalized,
        )
    root = acl.matching_root(normalized)
    if root is None:
        return FsDecision(
            allowed=False,
            reason="fs: path outside allowed roots",
            op=op,
            path=normalized,
        )
    if not root.allows(op):
        return FsDecision(
            allowed=False,
            reason=f"fs: {op} denied on {root.root}",
            op=op,
            path=normalized,
            root=root.root,
        )
    return FsDecision(allowed=True, op=op, path=normalized, root=root.root)


@dataclass
class MockFilesystem:
    """In-memory blobs gated by FilesystemAcl. Never returns another agent's content."""

    files: dict[str, str] = field(default_factory=dict)

    @classmethod
    def seeded(cls) -> MockFilesystem:
        return cls(
            files={
                "/agents/support/ticket.md": "Front ticket #1",
                "/agents/senior-dev/notes.md": "private senior-dev notes",
                "/agents/plan/spec.md": "plan spec",
                "/agents/default/scratch.md": "scratch",
            }
        )

    def apply(
        self,
        acl: FilesystemAcl,
        op: FsOp,
        path: str,
        content: str | None = None,
    ) -> dict[str, Any]:
        decision = evaluate_fs(acl, op, path)
        if not decision.allowed:
            return {
                "ok": False,
                "denied": True,
                "reason": decision.reason,
                "fs": {
                    "op": decision.op,
                    "path": decision.path,
                    "traversal": decision.traversal,
                    "root": decision.root,
                },
            }
        key = decision.path
        if op == "read":
            if key not in self.files:
                return {"ok": False, "reason": "fs: not found", "path": key}
            return {"ok": True, "path": key, "content": self.files[key]}
        if op == "write":
            self.files[key] = "" if content is None else str(content)
            return {"ok": True, "path": key, "bytes": len(self.files[key])}
        self.files.pop(key, None)
        return {"ok": True, "path": key, "deleted": True}


def gated_fs_output(
    acl: FilesystemAcl,
    op: FsOp,
    path: str,
    *,
    store: MockFilesystem | None = None,
    content: str | None = None,
) -> dict[str, Any]:
    fs = store if store is not None else MockFilesystem.seeded()
    return fs.apply(acl, op, path, content)
