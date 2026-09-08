import logging
import sys
import time
import uuid
from contextvars import ContextVar

import orjson
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

_REDACT_HEADERS = {"authorization", "cookie", "set-cookie"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return orjson.dumps(payload).decode()


def configure_logging(debug: bool) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    # Never let noisy libraries dump raw SQL (which can include bound params)
    # or auth headers at INFO/DEBUG in production.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


class RequestLoggingMiddleware:
    """Pure ASGI middleware (deliberately NOT `BaseHTTPMiddleware`).

    `BaseHTTPMiddleware` runs the downstream app in a separate task and
    bridges it back via a stream; an exception raised downstream can escape
    that bridge in a way that skips `ExceptionMiddleware` entirely, so a
    registered `@app.exception_handler(Exception)` never runs and the
    raw traceback falls through to Starlette's outer `ServerErrorMiddleware`
    (which, in debug mode, would render it straight into the HTTP response).
    A plain ASGI middleware sits inside `ExceptionMiddleware` in the stack
    like any other layer, so our JSON error handler always gets first
    crack at exceptions and no traceback is ever exposed to the client.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = headers.get("x-request-id", str(uuid.uuid4()))
        # Intentionally not reset via a token/finally: each HTTP request is
        # handled in its own asyncio Task (a fresh copy-on-write context),
        # so this can't leak into other requests. Resetting it here would
        # actually be harmful: if an exception propagates all the way out to
        # Starlette's ServerErrorMiddleware (outside this middleware), our
        # exception handler logs *after* this frame unwinds — a reset would
        # wipe request_id correlation right when it matters most (an
        # unhandled-exception log line).
        request_id_ctx.set(request_id)
        start = time.perf_counter()
        logger = logging.getLogger("gym.request")
        status_code = 0

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                mutable_headers = MutableHeaders(scope=message)
                mutable_headers.append("X-Request-ID", request_id)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "request_complete method=%s path=%s status=%s duration_ms=%s",
                scope.get("method"),
                scope.get("path"),
                status_code or "?",
                duration_ms,
            )
