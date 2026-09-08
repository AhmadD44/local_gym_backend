from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis

router = APIRouter(tags=["health"])


@router.get("/health", summary="Basic liveness/info endpoint")
async def health():
    return {"status": "ok"}


@router.get("/health/live", summary="Liveness probe (no dependency checks)")
async def liveness():
    return {"status": "alive"}


@router.get("/health/ready", summary="Readiness probe (checks DB and Redis)")
async def readiness(db: AsyncSession = Depends(get_db)):
    checks = {"database": "unknown", "redis": "unknown"}
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    try:
        redis = get_redis()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    status_ok = all(v == "ok" for v in checks.values())
    body = {"status": "ready" if status_ok else "not_ready", "checks": checks}
    return JSONResponse(status_code=200 if status_ok else 503, content=body)
