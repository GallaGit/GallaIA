import mimetypes
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.db.init_db import init_db
from app.exceptions.base import AppError
from app.exceptions.handlers import app_error_handler, unhandled_error_handler
from app.middleware.origin_guard import OriginGuardMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.api.dependencies.operator_auth import require_operator_token
from app.api.dependencies.settings import SettingsDep

settings = get_settings()
setup_logging(settings.log_level)
logger = get_logger(__name__)

# Explicit MIME types for the SPA: with ``X-Content-Type-Options: nosniff`` a wrong
# type is not "sniffed" back (on Windows the registry can map .js to text/plain).
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("application/manifest+json", ".webmanifest")

STATIC_DIR = Path(os.environ.get("STATIC_DIR", "static")).resolve()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting %s (env=%s, debug=%s)",
        settings.app_name,
        settings.app_env,
        settings.app_debug,
    )
    init_db()
    logger.info("Database ready (SQLite MVP; Postgres later)")
    if (STATIC_DIR / "index.html").is_file():
        logger.info("Serving UI from %s", STATIC_DIR)
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description="GallaAI AgentOS — control plane MVP (Phase 0+1)",
    lifespan=lifespan,
    # GALLAIA-SEC-008: no public API docs in production.
    docs_url=None if settings.app_env == "production" else "/docs",
    redoc_url=None if settings.app_env == "production" else "/redoc",
    openapi_url=None if settings.app_env == "production" else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Actor-Type",
        "X-Agent-Id",
        "X-Request-ID",
        "X-Webhook-Secret",
    ],
)
app.add_middleware(RequestIdMiddleware)
# GALLAIA-SEC-011: CSRF guard on state-changing /api/v1 calls + Host allow-list.
# Added last so they run first (outermost).
app.add_middleware(OriginGuardMiddleware, allowed_origins=settings.cors_origin_list)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_host_list)
# GALLAIA-SEC-007: CSP + security headers. Outermost, so even 400/403 from the
# guards above carry them. Pure ASGI: does not buffer SSE streams.
app.add_middleware(
    SecurityHeadersMiddleware,
    extra_connect_src=settings.csp_extra_connect_src_list,
)
app.include_router(
    api_router,
    prefix="/api/v1",
    dependencies=[Depends(require_operator_token)],
)


@app.get("/health")
def health(settings: SettingsDep):
    logger.debug("GET /health")
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
    }


def _spa_index() -> FileResponse | None:
    index = STATIC_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return None


@app.get("/")
def root():
    spa = _spa_index()
    if spa is not None:
        return spa
    logger.debug("GET /")
    return {"message": f"{settings.app_name} is running", "product": "AgentOS MVP"}


_assets_dir = STATIC_DIR / "assets"
if _assets_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    """Serve Vite SPA assets and client-side routes when STATIC_DIR is present."""
    if full_path.startswith("api/") or full_path in {
        "docs",
        "redoc",
        "openapi.json",
        "health",
    }:
        raise HTTPException(status_code=404, detail="Not Found")

    # GALLAIA-SEC-001: resolve and confine to STATIC_DIR (no path traversal).
    try:
        candidate = (STATIC_DIR / full_path).resolve()
    except (OSError, ValueError):
        raise HTTPException(status_code=404, detail="Not Found")
    if not candidate.is_relative_to(STATIC_DIR):
        raise HTTPException(status_code=404, detail="Not Found")
    if candidate.is_file():
        return FileResponse(candidate)

    spa = _spa_index()
    if spa is not None:
        return spa
    raise HTTPException(status_code=404, detail="Not Found")


app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)
