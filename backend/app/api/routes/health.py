from fastapi import APIRouter
from sqlalchemy import text

from app.api.dependencies.db import DbSession
from app.api.dependencies.settings import SettingsDep
from app.exceptions import NotFoundError

router = APIRouter(tags=["health"])


@router.get("/health")
def api_health(settings: SettingsDep, db: DbSession):
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "api_version": "v1",
        "database": "ok",
    }


@router.get("/demo-error")
def demo_error():
    raise NotFoundError("Demo resource was not found")