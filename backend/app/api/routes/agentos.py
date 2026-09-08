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

router = APIRouter(prefix="/agentos", tags=["agentos"])


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
def get_agents() -> list[AgentSeedOut]:
    """List seeded agents (default, plan, senior-dev)."""
    return [
        AgentSeedOut(
            name=s.name,
            title=s.title,
            model=s.model,
            one_job=s.one_job,
            skills=list(s.skills),
            mcp=list(s.mcp),
            runner_preference=s.runner_preference,
            prompt_origin=s.prompt_origin,
            foundational_prompt=s.foundational_prompt,
            role_prompt=s.role_prompt,
        )
        for s in list_seeds()
    ]


@router.get("/agents/{name}", response_model=AgentSeedOut)
def get_agent(name: str) -> AgentSeedOut:
    try:
        s = get_seed(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AgentSeedOut(
        name=s.name,
        title=s.title,
        model=s.model,
        one_job=s.one_job,
        skills=list(s.skills),
        mcp=list(s.mcp),
        runner_preference=s.runner_preference,
        prompt_origin=s.prompt_origin,
        foundational_prompt=s.foundational_prompt,
        role_prompt=s.role_prompt,
    )


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
def run_task(task_id: str, body: RunRequest | None = None) -> RunResponse:
    body = body or RunRequest()
    runner = SessionRunner(store)
    try:
        result = runner.run(
            task_id,
            agent_name=body.agent_name,
            runner=body.runner,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RunResponse(
        runner=result.runner,
        used_anthropic=result.used_anthropic,
        summary=result.summary,
        task=_task_out(result.task),
        session=_session_out(result.session),
    )


@router.get("/sessions/{session_id}", response_model=SessionOut)
def get_session(session_id: str) -> SessionOut:
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Unknown session {session_id!r}")
    return _session_out(session)
