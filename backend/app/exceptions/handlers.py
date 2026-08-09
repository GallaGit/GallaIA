from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.exceptions.base import AppError

logger = get_logger(__name__)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning(
        "AppError on %s %s: %s (%s)",
        request.method,
        request.url.path,
        exc.message,
        exc.code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
            }
        },
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last resort: never leak stack traces to the client."""
    logger.exception(
        "Unhandled error on %s %s",
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "Internal server error",
            }
        },
    )