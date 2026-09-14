"""AgentOS MVP HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.agentos.models import Task
from app.agentos.runner import SessionRunner
from app.agentos.schemas import (
    AgentSeedOut,
    RunRequest,
    RunResponse,
    SessionOut,
    InboxItem,
    TaskCreate,
    TaskOut,
    TaskUpdate,
    ToolEventOut,
)
from app.agentos.seeds import get_seed, list_seeds
from app.agentos.store import store
from app.api.dependencies.db import DbSession
from app.agentos.secrets import UnresolvedSecretRef
from app.exceptions import UnresolvedSecretRefError
from app.schemas.filesystem import AgentFsOut, AgentFsUpdate
from app.schemas.grant import AgentGrantsOut, AgentGrantsUpdate
from app.schemas.network import AgentNetworkOut, AgentNetworkUpdate
from app.schemas.secret import AgentSecretsOut, AgentSecretsUpdate
from app.services.filesystem import filesystem_acl_for_agent, fs_out, replace_agent_fs
from app.services.grants import (
    grant_set_for_agent,
    grants_out,
    load_agent_by_name,
    replace_agent_grants,
    require_agent_by_name,
)
from app.services.network import (
    network_out,
    network_policy_for_agent,
    replace_agent_network,
)
from app.services.secrets import (
    replace_agent_secrets,
    secret_refs_for_agent,
    secrets_out,
)
from app.services.skills import resolve_skill_slugs

router = APIRouter(prefix="/agentos", tags=["agentos"])


def _seed_out(s, db=None) -> AgentSeedOut:
    resolved: list[dict[str, str]] = []
    if db is not None and s.skills:
        for row in resolve_skill_slugs(db, s.skills):
            resolved.append(
                {
                    "slug": row.slug,
                    "name": row.name,
                    "kind": row.kind,
                    "body": row.body,
                }
            )
    return AgentSeedOut(
        name=s.name,
        title=s.title,
        model=s.model,
        one_job=s.one_job,
        skills=list(s.skills),
        resolved_skills=resolved,
        mcp=list(s.mcp),
        grants=s.grant_set().as_list(),
        network_mode=s.network_mode,
        network_allowlist=list(s.network_allowlist),
        fs_acl=s.filesystem_acl().as_list(),
        secrets=s.secret_ref_set().as_list(),
        runner_preference=s.runner_preference,
        prompt_origin=s.prompt_origin,
        foundational_prompt=s.foundational_prompt,
        role_prompt=s.role_prompt,
    )


def _task_out(task: Task) -> TaskOut:
    return TaskOut(
        id=task.id,
        name=task.name,
        description=task.description,
        assignee_agent=task.assignee_agent,
        status=task.status,
        activity=list(task.activity),
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _session_out(session) -> SessionOut:
    return SessionOut(
        id=session.id,
        task_id=session.task_id,
        agent_name=session.agent_name,
        runner=session.runner,
        status=session.status,
        summary=session.summary,
        tool_events=[
            ToolEventOut(
                name=e.name, input=e.input, output=e.output, at=e.at
            )
            for e in session.tool_events
        ],
        started_at=session.started_at,
        ended_at=session.ended_at,
    )


@router.get("/agents", response_model=list[AgentSeedOut])
def get_agents(db: DbSession) -> list[AgentSeedOut]:
    """List seeded agents (default, plan, senior-dev, support)."""
    return [_seed_out(s, db) for s in list_seeds()]


@router.get("/agents/{name}", response_model=AgentSeedOut)
def get_agent(name: str, db: DbSession) -> AgentSeedOut:
    try:
        s = get_seed(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _seed_out(s, db)


@router.get("/agents/{name}/grants", response_model=AgentGrantsOut)
def get_agent_grants(name: str, db: DbSession) -> AgentGrantsOut:
    return grants_out(require_agent_by_name(db, name))


@router.put("/agents/{name}/grants", response_model=AgentGrantsOut)
def put_agent_grants(
    name: str, body: AgentGrantsUpdate, db: DbSession
) -> AgentGrantsOut:
    agent = require_agent_by_name(db, name)
    return replace_agent_grants(db, agent, body.grants)


@router.get("/agents/{name}/network", response_model=AgentNetworkOut)
def get_agent_network(name: str, db: DbSession) -> AgentNetworkOut:
    return network_out(require_agent_by_name(db, name))


@router.put("/agents/{name}/network", response_model=AgentNetworkOut)
def put_agent_network(
    name: str, body: AgentNetworkUpdate, db: DbSession
) -> AgentNetworkOut:
    agent = require_agent_by_name(db, name)
    return replace_agent_network(db, agent, body.mode, body.allowlist)


@router.get("/agents/{name}/fs", response_model=AgentFsOut)
def get_agent_fs(name: str, db: DbSession) -> AgentFsOut:
    return fs_out(require_agent_by_name(db, name))


@router.put("/agents/{name}/fs", response_model=AgentFsOut)
def put_agent_fs(name: str, body: AgentFsUpdate, db: DbSession) -> AgentFsOut:
    agent = require_agent_by_name(db, name)
    return replace_agent_fs(db, agent, body.roots)


@router.get("/agents/{name}/secrets", response_model=AgentSecretsOut)
def get_agent_secrets(name: str, db: DbSession) -> AgentSecretsOut:
    return secrets_out(require_agent_by_name(db, name))


@router.put("/agents/{name}/secrets", response_model=AgentSecretsOut)
def put_agent_secrets(
    name: str, body: AgentSecretsUpdate, db: DbSession
) -> AgentSecretsOut:
    agent = require_agent_by_name(db, name)
    return replace_agent_secrets(db, agent, body.secrets)


@router.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(body: TaskCreate) -> TaskOut:
    try:
        get_seed(body.assignee_agent)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    task = Task(
        name=body.name,
        description=body.description,
        assignee_agent=body.assignee_agent,
    )
    store.create_task(task)
    return _task_out(task)


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks() -> list[TaskOut]:
    return [_task_out(t) for t in store.list_tasks()]


@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: str) -> TaskOut:
    task = store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Unknown task {task_id!r}")
    return _task_out(task)




@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: str, body: TaskUpdate) -> TaskOut:
    task = store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Unknown task {task_id!r}")
    if body.assignee_agent is not None:
        try:
            get_seed(body.assignee_agent)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        task.assignee_agent = body.assignee_agent
        task.activity.append(f"assigned:{body.assignee_agent}")
    if body.status is not None:
        task.status = body.status
        task.activity.append(f"status:{body.status}")
    store.save_task(task)
    return _task_out(task)


@router.get("/inbox", response_model=list[InboxItem])
def get_inbox() -> list[InboxItem]:
    """Minimal inbox: sessions waiting on human + tasks in review."""
    items: list[InboxItem] = []
    tasks = {t.id: t for t in store.list_tasks()}
    for session in store.list_sessions():
        if session.status != "waiting-inbox":
            continue
        task = tasks.get(session.task_id)
        title = task.name if task else session.task_id
        items.append(
            InboxItem(
                id=session.id,
                kind="session",
                task_id=session.task_id,
                title=title,
                status=session.status,
                message=session.summary or "Waiting for inbox approval",
                created_at=session.started_at,
            )
        )
    for task in store.list_tasks():
        if task.status != "review":
            continue
        items.append(
            InboxItem(
                id=task.id,
                kind="task",
                task_id=task.id,
                title=task.name,
                status=task.status,
                message=(task.activity[-1] if task.activity else "Needs review"),
                created_at=task.updated_at,
            )
        )
    items.sort(key=lambda i: i.created_at, reverse=True)
    return items

@router.post("/tasks/{task_id}/run", response_model=RunResponse)
def run_task(
    task_id: str, db: DbSession, body: RunRequest | None = None
) -> RunResponse:
    body = body or RunRequest()
    task = store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Unknown task {task_id!r}")
    seed_name = body.agent_name or task.assignee_agent
    stored = load_agent_by_name(db, seed_name)
    grants = grant_set_for_agent(stored) if stored is not None else None
    network = network_policy_for_agent(stored) if stored is not None else None
    filesystem = filesystem_acl_for_agent(stored) if stored is not None else None
    secrets = secret_refs_for_agent(stored) if stored is not None else None
    runner = SessionRunner(store)
    try:
        result = runner.run(
            task_id,
            agent_name=body.agent_name,
            runner=body.runner,
            grants=grants,
            network=network,
            filesystem=filesystem,
            secrets=secrets,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnresolvedSecretRef as exc:
        raise UnresolvedSecretRefError(list(exc.missing)) from exc
    return RunResponse(
        runner=result.runner,
        used_anthropic=result.used_anthropic,
        used_openrouter=result.used_openrouter,
        summary=result.summary,
        task=_task_out(result.task),
        session=_session_out(result.session),
    )




@router.get("/sessions", response_model=list[SessionOut])
def list_sessions() -> list[SessionOut]:
    return [_session_out(s) for s in store.list_sessions()]

@router.get("/sessions/{session_id}", response_model=SessionOut)
def get_session(session_id: str) -> SessionOut:
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Unknown session {session_id!r}")
    return _session_out(session)
