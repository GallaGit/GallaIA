from fastapi import APIRouter
from sqlalchemy import select

from app.api.dependencies.db import DbSession
from app.exceptions import BadRequestError, NotFoundError
from app.models import Agent, Project, Task
from app.models.task import TASK_STATUSES
from app.schemas import SessionOut, TaskCreate, TaskOut, TaskStatusUpdate, TaskUpdate
from app.services.runner import run_task_session

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _default_project_id(db: DbSession) -> int:
    project = db.scalar(select(Project).where(Project.slug == "default"))
    if project is None:
        raise BadRequestError("Default project missing — restart backend to seed")
    return project.id


@router.get("", response_model=list[TaskOut])
def list_tasks(db: DbSession, project_id: int | None = None, status: str | None = None):
    stmt = select(Task).order_by(Task.id)
    if project_id is not None:
        stmt = stmt.where(Task.project_id == project_id)
    if status is not None:
        if status not in TASK_STATUSES:
            raise BadRequestError(f"Invalid status: {status}")
        stmt = stmt.where(Task.status == status)
    return list(db.scalars(stmt).all())


@router.post("", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate, db: DbSession):
    project_id = payload.project_id or _default_project_id(db)
    if db.get(Project, project_id) is None:
        raise NotFoundError(f"Project {project_id} not found")
    if payload.assignee_agent_id is not None and db.get(Agent, payload.assignee_agent_id) is None:
        raise NotFoundError(f"Agent {payload.assignee_agent_id} not found")

    task = Task(
        project_id=project_id,
        name=payload.name,
        description=payload.description,
        assignee_agent_id=payload.assignee_agent_id,
        approval_gate=payload.approval_gate,
        status="todo",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: DbSession):
    task = db.get(Task, task_id)
    if task is None:
        raise NotFoundError(f"Task {task_id} not found")
    return task


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate, db: DbSession):
    task = db.get(Task, task_id)
    if task is None:
        raise NotFoundError(f"Task {task_id} not found")
    data = payload.model_dump(exclude_unset=True)
    if "assignee_agent_id" in data and data["assignee_agent_id"] is not None:
        if db.get(Agent, data["assignee_agent_id"]) is None:
            raise NotFoundError(f"Agent {data['assignee_agent_id']} not found")
    for key, value in data.items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}/status", response_model=TaskOut)
def patch_task_status(task_id: int, payload: TaskStatusUpdate, db: DbSession):
    task = db.get(Task, task_id)
    if task is None:
        raise NotFoundError(f"Task {task_id} not found")
    if payload.status not in TASK_STATUSES:
        raise BadRequestError(f"Invalid status: {payload.status}")
    task.status = payload.status
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, db: DbSession):
    task = db.get(Task, task_id)
    if task is None:
        raise NotFoundError(f"Task {task_id} not found")
    db.delete(task)
    db.commit()


@router.post("/{task_id}/run", response_model=SessionOut)
def run_task(task_id: int, db: DbSession):
    task = db.get(Task, task_id)
    if task is None:
        raise NotFoundError(f"Task {task_id} not found")
    if task.assignee_agent_id is None:
        raise BadRequestError("Task has no assigned agent")
    agent = db.get(Agent, task.assignee_agent_id)
    if agent is None:
        raise NotFoundError(f"Agent {task.assignee_agent_id} not found")
    session = run_task_session(db, task, agent)
    return session
