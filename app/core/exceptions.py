import logging
from collections.abc import Sequence

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger("gym.errors")

# Field names whose submitted value must never be echoed back in a 422
# response body. Pydantic v2's default error output includes the raw
# `input` that failed validation (e.g. a too-short password), which would
# otherwise round-trip a plaintext secret straight back to the client —
# and from there into browser devtools, proxy/APM logs, etc.
_SENSITIVE_FIELD_NAMES = {"password", "new_password", "current_password", "token", "refresh_token"}


def _redact_validation_errors(errors: Sequence[dict]) -> list[dict]:
    redacted = []
    for error in errors:
        loc = error.get("loc", ())
        if any(str(part).lower() in _SENSITIVE_FIELD_NAMES for part in loc):
            error = {**error, "input": "[redacted]"}
        redacted.append(error)
    return redacted


class AppError(HTTPException):
    """Base application error with a stable machine-readable `code`."""

    def __init__(self, status_code: int, code: str, message: str, headers: dict | None = None):
        super().__init__(status_code=status_code, detail={"code": code, "message": message}, headers=headers)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(status.HTTP_404_NOT_FOUND, "not_found", message)


class ForbiddenError(AppError):
    def __init__(self, message: str = "You do not have access to this resource"):
        super().__init__(status.HTTP_403_FORBIDDEN, "forbidden", message)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, "unauthorized", message)


class ConflictError(AppError):
    def __init__(self, message: str = "Conflicting state"):
        super().__init__(status.HTTP_409_CONFLICT, "conflict", message)


class BadRequestError(AppError):
    def __init__(self, message: str = "Invalid request"):
        super().__init__(status.HTTP_400_BAD_REQUEST, "bad_request", message)


class RateLimitedError(AppError):
    def __init__(self, message: str = "Too many requests", retry_after: int | None = None):
        headers = {"Retry-After": str(retry_after)} if retry_after else None
        super().__init__(status.HTTP_429_TOO_MANY_REQUESTS, "rate_limited", message, headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail}, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        details = _redact_validation_errors(exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"error": {"code": "validation_error", "message": "Invalid input", "details": details}},
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        logger.warning("integrity_error path=%s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": {"code": "conflict", "message": "The request conflicts with existing data"}},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        logger.exception("unhandled_error path=%s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": "internal_error", "message": "An unexpected error occurred"}},
        )
