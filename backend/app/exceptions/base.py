class AppError(Exception):
    """Base application error (safe to map to an HTTP response)."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "app_error",
        status_code: int = 400,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, code="not_found", status_code=404)


class BadRequestError(AppError):
    def __init__(self, message: str = "Bad request") -> None:
        super().__init__(message, code="bad_request", status_code=400)


class UnresolvedSecretRefError(AppError):
    """Session start denied because a secret ref has no value in env/fixture."""

    def __init__(self, names: list[str] | tuple[str, ...] | None = None) -> None:
        listed = ", ".join(names) if names else "(unknown)"
        super().__init__(
            f"unresolved secret ref: {listed}",
            code="unresolved_secret_ref",
            status_code=403,
        )
        self.names = tuple(names or ())


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message, code="forbidden", status_code=403)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message, code="unauthorized", status_code=401)

