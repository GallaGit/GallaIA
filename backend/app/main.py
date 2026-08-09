from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import get_logger, setup_logging

settings = get_settings()
setup_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting %s (env=%s, debug=%s)",
        settings.app_name,
        settings.app_env,
        settings.app_debug,
    )
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Backend de GallaAI — Fase 1 Foundation",
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
    logger.debug("GET /")
    return {"message": f"{settings.app_name} is running"}


@app.get("/health")
def health(settings: Settings = Depends(get_settings)):
    logger.debug("GET /health")
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
    }