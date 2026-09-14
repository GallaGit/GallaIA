"""Load and replace per-agent filesystem ACLs in SQLite. Empty list = default deny."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agentos.filesystem import FilesystemAcl, FsRoot, normalize_root
from app.exceptions import BadRequestError
from app.models import Agent, AgentFsAcl
from app.schemas.filesystem import AgentFsOut, FsRootItem
from app.services.grants import require_agent, require_agent_by_name

__all__ = [
    "filesystem_acl_for_agent",
    "fs_out",
    "replace_agent_fs",
    "require_agent",
    "require_agent_by_name",
]


def filesystem_acl_from_rows(rows: list[AgentFsAcl] | None) -> FilesystemAcl:
    if not rows:
        return FilesystemAcl.empty()
    return FilesystemAcl.from_roots(
        FsRoot(
            root=row.root,
            can_read=row.can_read,
            can_write=row.can_write,
            can_delete=row.can_delete,
        )
        for row in rows
    )


def filesystem_acl_for_agent(agent: Agent | None) -> FilesystemAcl:
    if agent is None:
        return FilesystemAcl.empty()
    return filesystem_acl_from_rows(list(agent.fs_acls or []))


def fs_out(agent: Agent) -> AgentFsOut:
    acl = filesystem_acl_for_agent(agent)
    return AgentFsOut(
        agent_id=agent.id,
        agent_name=agent.name,
        roots=[FsRootItem.model_validate(row) for row in acl.as_list()],
    )


def replace_agent_fs(db: Session, agent: Agent, roots: list[FsRootItem]) -> AgentFsOut:
    normalized: list[FsRoot] = []
    seen: set[str] = set()
    for item in roots:
        try:
            root = normalize_root(item.root)
        except ValueError as exc:
            raise BadRequestError(str(exc)) from exc
        if root in seen:
            raise BadRequestError(f"Duplicate filesystem root: {root}")
        seen.add(root)
        normalized.append(
            FsRoot(
                root=root,
                can_read=bool(item.can_read),
                can_write=bool(item.can_write),
                can_delete=bool(item.can_delete),
            )
        )

    for row in list(agent.fs_acls):
        db.delete(row)
    db.flush()
    for root in normalized:
        db.add(
            AgentFsAcl(
                agent_id=agent.id,
                root=root.root,
                can_read=root.can_read,
                can_write=root.can_write,
                can_delete=root.can_delete,
            )
        )
    db.commit()
    db.refresh(agent)
    return fs_out(agent)
