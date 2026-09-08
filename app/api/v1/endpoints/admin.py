from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.pagination import Page, PageParams, paginate
from app.core.permissions import require_admin
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.dashboard import AdminDashboardResponse
from app.schemas.profiles import CreateStaffRequest
from app.services import auth_service
from app.services.dashboard_service import get_admin_dashboard

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.post("/staff", status_code=201, summary="Create a TRAINER or ADMIN account (admin only)")
async def create_staff(
    payload: CreateStaffRequest, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)
):
    payload.validate_creatable_role()
    user = await auth_service.create_staff_user(
        db,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        role=payload.role,
        actor_id=admin.id,
    )
    return {"id": user.id, "email": user.email, "role": user.role}


@router.get("/dashboard", response_model=AdminDashboardResponse, summary="Admin analytics dashboard")
async def admin_dashboard(db: AsyncSession = Depends(get_db)):
    return await get_admin_dashboard(db)


@router.get("/audit-logs", summary="List audit logs (admin only)")
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    entity_type: str | None = None,
    action: str | None = None,
):
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if action:
        stmt = stmt.where(AuditLog.action == action)

    params = PageParams(page=page, page_size=page_size)
    items, total = await paginate(db, stmt, params)
    serialized = [
        {
            "id": str(log.id),
            "actor_id": str(log.actor_id) if log.actor_id else None,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "before": log.before,
            "after": log.after,
            "created_at": log.created_at.isoformat(),
        }
        for log in items
    ]
    return Page.create(serialized, total, params)
