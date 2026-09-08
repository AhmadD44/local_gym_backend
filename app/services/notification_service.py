import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.enums import DevicePlatform, NotificationType
from app.models.notification import DeviceToken, Notification
from app.services.push_provider import get_push_provider


async def create_notification(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    type_: NotificationType,
    title: str,
    body: str,
    data: dict | None = None,
    dispatch_push: bool = True,
) -> Notification:
    notification = Notification(
        user_id=user_id, type=type_, title=title, body=body, data=data, created_at=datetime.now(UTC)
    )
    session.add(notification)
    await session.commit()
    await session.refresh(notification)

    if dispatch_push:
        await _dispatch_push(session, user_id=user_id, title=title, body=body, data=data)
    return notification


async def _dispatch_push(
    session: AsyncSession, *, user_id: uuid.UUID, title: str, body: str, data: dict | None
) -> None:
    result = await session.execute(select(DeviceToken.token).where(DeviceToken.user_id == user_id))
    tokens = list(result.scalars().all())
    if not tokens:
        return
    provider = get_push_provider()
    await provider.send(tokens=tokens, title=title, body=body, data=data)


async def list_notifications(session: AsyncSession, *, user_id: uuid.UUID) -> list[Notification]:
    result = await session.execute(
        select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc())
    )
    return list(result.scalars().all())


async def mark_notification_read(
    session: AsyncSession, *, notification_id: uuid.UUID, user_id: uuid.UUID
) -> Notification:
    notification = await session.get(Notification, notification_id)
    if notification is None or notification.user_id != user_id:
        raise NotFoundError("Notification not found")
    notification.read_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(notification)
    return notification


async def register_device_token(
    session: AsyncSession, *, user_id: uuid.UUID, token: str, platform: DevicePlatform
) -> DeviceToken:
    existing = await session.execute(
        select(DeviceToken).where(DeviceToken.user_id == user_id, DeviceToken.token == token)
    )
    device = existing.scalar_one_or_none()
    if device is not None:
        return device
    device = DeviceToken(user_id=user_id, token=token, platform=platform, created_at=datetime.now(UTC))
    session.add(device)
    await session.commit()
    await session.refresh(device)
    return device
