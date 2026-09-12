import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ClassBookingStatus
from app.schemas.common import TimestampedModel
from app.schemas.profiles import MemberProfileRead, TrainerProfileRead


class GymClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    trainer_id: uuid.UUID
    capacity: int = Field(gt=0, le=500)
    location: str | None = None
    start_time: datetime
    end_time: datetime


class GymClassUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    trainer_id: uuid.UUID | None = None
    capacity: int | None = Field(default=None, gt=0, le=500)
    location: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_active: bool | None = None


class GymClassRead(TimestampedModel):
    name: str
    description: str | None
    trainer_id: uuid.UUID
    trainer: TrainerProfileRead
    capacity: int
    location: str | None
    start_time: datetime
    end_time: datetime
    is_active: bool
    booked_count: int = 0
    available_spots: int = 0


class ClassBookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    class_id: uuid.UUID
    member_id: uuid.UUID
    status: ClassBookingStatus
    booked_at: datetime
    cancelled_at: datetime | None


class ClassBookingAdminRead(ClassBookingRead):
    """Same as ClassBookingRead but with the member's profile embedded —
    used for the admin roster view (who's booked into this class), where
    a bare member_id isn't useful at the front desk."""

    member: MemberProfileRead
