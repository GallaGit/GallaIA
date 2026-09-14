from fastapi import APIRouter

from app.api.dependencies.db import DbSession
from app.schemas.skill import SkillCreate, SkillOut, SkillUpdate, SkillUpsert
from app.services.skills import (
    create_skill,
    delete_skill,
    get_skill,
    list_skills,
    skill_out,
    update_skill,
    upsert_skill,
)

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillOut])
def api_list_skills(db: DbSession):
    return [skill_out(s) for s in list_skills(db)]


@router.get("/{skill_key}", response_model=SkillOut)
def api_get_skill(skill_key: str, db: DbSession):
    return skill_out(get_skill(db, skill_key))


@router.post("", response_model=SkillOut, status_code=201)
def api_create_skill(payload: SkillCreate, db: DbSession):
    return skill_out(create_skill(db, payload))


@router.patch("/{skill_key}", response_model=SkillOut)
def api_update_skill(skill_key: str, payload: SkillUpdate, db: DbSession):
    return skill_out(update_skill(db, skill_key, payload))


@router.put("/{slug}", response_model=SkillOut)
def api_upsert_skill(slug: str, payload: SkillUpsert, db: DbSession):
    return skill_out(upsert_skill(db, slug, payload))


@router.delete("/{skill_key}", status_code=204)
def api_delete_skill(skill_key: str, db: DbSession):
    delete_skill(db, skill_key)
