from fastapi import APIRouter
from sqlalchemy import select

from app.api.dependencies.db import DbSession
from app.exceptions import NotFoundError
from app.models import Project
from app.schemas import ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_projects(db: DbSession):
    return list(db.scalars(select(Project).order_by(Project.id)).all())


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: DbSession):
    project = db.get(Project, project_id)
    if project is None:
        raise NotFoundError(f"Project {project_id} not found")
    return project
