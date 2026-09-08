from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import DevicePlatform, NotificationType
from app.schemas.common import IDModel


class NotificationRead(IDModel):
    type: NotificationType
    title: str
    body: str
    data: dict | None
    read_at: datetime | None
    created_at: datetime


class DeviceTokenRegister(BaseModel):
    token: str = Field(min_length=1, max_length=500)
    platform: DevicePlatform
