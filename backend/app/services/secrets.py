"""Load and replace per-agent secret refs in SQLite. Values never persist."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agentos.secrets import (
    SECRET_PROVIDERS,
    SecretRef,
    SecretRefSet,
    UnresolvedSecretRef,
    normalize_provider,
    normalize_ref_ident,
    resolve_secret_refs,
)
from app.exceptions import BadRequestError, UnresolvedSecretRefError
from app.models import Agent, AgentSecretRef
from app.schemas.secret import AgentSecretsOut, SecretRefItem
from app.services.grants import require_agent, require_agent_by_name

__all__ = [
    "secret_refs_for_agent",
    "secrets_out",
    "replace_agent_secrets",
    "resolve_agent_secrets",
    "require_agent",
    "require_agent_by_name",
]


def secret_refs_from_rows(rows: list[AgentSecretRef] | None) -> SecretRefSet:
    if not rows:
        return SecretRefSet.empty()
    return SecretRefSet.from_items(
        SecretRef(name=row.name, provider=row.provider, key=row.key)  # type: ignore[arg-type]
        for row in rows
    )


def secret_refs_for_agent(agent: Agent | None) -> SecretRefSet:
    if agent is None:
        return SecretRefSet.empty()
    return secret_refs_from_rows(list(agent.secret_refs or []))


def secrets_out(agent: Agent) -> AgentSecretsOut:
    refs = secret_refs_for_agent(agent)
    return AgentSecretsOut(
        agent_id=agent.id,
        agent_name=agent.name,
        secrets=[SecretRefItem.model_validate(row) for row in refs.as_list()],
    )


def replace_agent_secrets(
    db: Session, agent: Agent, items: list[SecretRefItem]
) -> AgentSecretsOut:
    normalized: list[SecretRef] = []
    seen: set[str] = set()
    for item in items:
        payload = item.model_dump()
        if "value" in payload:
            raise BadRequestError("Secret values are not stored; send a name/key ref only")
        try:
            name = normalize_ref_ident(item.name, field="name")
            provider = normalize_provider(item.provider)
            key = normalize_ref_ident(item.key or item.name, field="key")
        except ValueError as exc:
            raise BadRequestError(str(exc)) from exc
        if provider not in SECRET_PROVIDERS:
            raise BadRequestError(f"Invalid secret provider: {item.provider}")
        if name in seen:
            raise BadRequestError(f"Duplicate secret ref name: {name}")
        seen.add(name)
        normalized.append(SecretRef(name=name, provider=provider, key=key))

    for row in list(agent.secret_refs):
        db.delete(row)
    db.flush()
    for ref in normalized:
        db.add(
            AgentSecretRef(
                agent_id=agent.id,
                name=ref.name,
                provider=ref.provider,
                key=ref.key,
            )
        )
    db.commit()
    db.refresh(agent)
    return secrets_out(agent)


def resolve_agent_secrets(
    agent: Agent | None,
    *,
    environ: dict[str, str] | None = None,
    fixture: dict[str, str] | None = None,
):
    refs = secret_refs_for_agent(agent)
    try:
        return resolve_secret_refs(refs, environ=environ, fixture=fixture)
    except UnresolvedSecretRef as exc:
        raise UnresolvedSecretRefError(list(exc.missing)) from exc
