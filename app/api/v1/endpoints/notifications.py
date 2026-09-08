import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import get_current_active_user
from app.models.user import User
from app.schemas.notification import DeviceTokenRegister, NotificationRead
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead], summary="List my notifications")
async def list_notifications(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_active_user)):
    return await notification_service.list_notifications(db, user_id=user.id)


@router.post("/{notification_id}/read", response_model=NotificationRead, summary="Mark a notification as read")
async def mark_read(
    notification_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_active_user)
):
    return await notification_service.mark_notification_read(db, notification_id=notification_id, user_id=user.id)


@router.post("/devices", status_code=201, summary="Register a push notification device token")
async def register_device(
    payload: DeviceTokenRegister, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_active_user)
):
    device = await notification_service.register_device_token(
        db, user_id=user.id, token=payload.token, platform=payload.platform
    )
    return {"id": device.id}
