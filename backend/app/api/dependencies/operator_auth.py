"""Operator bearer-token gate for /api/v1 routes."""

import secrets

from fastapi import HTTPException, Request

from app.api.dependencies.settings import SettingsDep

WEBHOOK_PATH = "/api/v1/triggers/webhook"
_WWW_AUTHENTICATE = {"WWW-Authenticate": "Bearer"}


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=401, detail="Unauthorized", headers=_WWW_AUTHENTICATE)


def require_operator_token(request: Request, settings: SettingsDep) -> None:
    """Require a valid operator bearer token, except for the webhook route."""
    if request.url.path == WEBHOOK_PATH:
        return

    authorization = request.headers.get("Authorization")
    if not authorization:
        raise _unauthorized()

    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer":
        raise _unauthorized()

    token = token.strip()
    if not token:
        raise _unauthorized()

    if not secrets.compare_digest(
        token.encode(),
        settings.gallaia_operator_token.encode(),
    ):
        raise _unauthorized()
