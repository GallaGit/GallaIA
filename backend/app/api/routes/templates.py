from fastapi import APIRouter

from app.api.dependencies.db import DbSession
from app.schemas.template import TemplateInstantiateIn, TemplateInstantiateOut, TemplateOut
from app.services.templates import (
    get_template,
    instantiate_template,
    list_templates,
    template_out,
)

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=list[TemplateOut])
def api_list_templates(db: DbSession, project_id: int | None = None):
    return [template_out(t) for t in list_templates(db, project_id=project_id)]


@router.get("/{template_key}", response_model=TemplateOut)
def api_get_template(template_key: str, db: DbSession):
    return template_out(get_template(db, template_key))


@router.post(
    "/{template_key}/instantiate",
    response_model=TemplateInstantiateOut,
    status_code=201,
)
def api_instantiate_template(
    template_key: str,
    db: DbSession,
    payload: TemplateInstantiateIn | None = None,
):
    body = payload or TemplateInstantiateIn()
    template = get_template(db, template_key)
    return instantiate_template(
        db,
        template,
        project_id=body.project_id,
        name_prefix=body.name_prefix,
    )
