import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.endpoints import health
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import RequestLoggingMiddleware, configure_logging
from app.tasks.membership_expiry import run_forever as run_membership_expiry_sweep
from app.websocket.chat_ws import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.debug)
    task = asyncio.create_task(run_membership_expiry_sweep())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(
    title=settings.app_name,
    description=(
        "Production-oriented backend for a Gym Management System: memberships (cash "
        "payment), trainers, workouts, progress tracking, classes, chat, notifications, "
        "a store with cash-on-delivery orders, promotions, and gym information — designed "
        "for a Flutter mobile client."
    ),
    version="1.0.0",
    # Deliberately always False, independent of settings.debug (which only
    # controls log verbosity / the forgot-password debug token). Starlette's
    # ServerErrorMiddleware renders a raw HTML traceback straight into the
    # HTTP response whenever debug=True, completely bypassing our
    # `register_exception_handlers` JSON error handler below — that would
    # leak stack traces (and anything embedded in exception messages) to
    # clients. Server-side tracebacks are still fully available via
    # structured logs (see unhandled_error_handler's logger.exception call).
    debug=False,
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

if settings.cors_origin_list:
    if "*" in settings.cors_origin_list:
        raise RuntimeError(
            "CORS_ORIGINS must not contain '*'; list explicit allowed origins instead "
            "(e.g. https://app.example.com). A wildcard origin is a real security risk "
            "even without credentials, since it lets any website call this API from a "
            "logged-in user's browser."
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        # No cookies are used for authentication (the API is Bearer-token
        # only), so `allow_credentials` is deliberately left at its default
        # of False. This also sidesteps the classic "wildcard origin +
        # credentials" CORS misconfiguration entirely, since credentialed
        # CORS is never in play here.
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(RequestLoggingMiddleware)

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(api_router, prefix=settings.api_prefix)
app.include_router(ws_router, prefix=settings.api_prefix)

if settings.storage_backend == "local":
    import os

    os.makedirs(settings.storage_local_dir, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.storage_local_dir), name="uploads")
