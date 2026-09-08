import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.common import IDModel


class BodyMeasurementCreate(BaseModel):
    recorded_at: datetime
    weight_kg: float | None = Field(default=None, gt=0, lt=500)
    body_fat_pct: float | None = Field(default=None, ge=0, le=100)
    chest_cm: float | None = Field(default=None, gt=0, lt=300)
    waist_cm: float | None = Field(default=None, gt=0, lt=300)
    hips_cm: float | None = Field(default=None, gt=0, lt=300)
    arms_cm: float | None = Field(default=None, gt=0, lt=200)
    thighs_cm: float | None = Field(default=None, gt=0, lt=200)
    notes: str | None = None


class BodyMeasurementRead(IDModel):
    member_id: uuid.UUID
    recorded_at: datetime
    weight_kg: float | None
    body_fat_pct: float | None
    chest_cm: float | None
    waist_cm: float | None
    hips_cm: float | None
    arms_cm: float | None
    thighs_cm: float | None
    notes: str | None
    recorded_by: uuid.UUID | None


class ProgressPhotoCreate(BaseModel):
    photo_url: str
    taken_at: datetime
    notes: str | None = None


class ProgressPhotoRead(IDModel):
    member_id: uuid.UUID
    photo_url: str
    taken_at: datetime
    notes: str | None


class PersonalRecordCreate(BaseModel):
    exercise_id: uuid.UUID
    value: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=20)
    achieved_at: date


class PersonalRecordRead(IDModel):
    member_id: uuid.UUID
    exercise_id: uuid.UUID
    value: float
    unit: str
    achieved_at: date


class AchievementRead(IDModel):
    name: str
    description: str | None
    icon: str | None


class MemberAchievementRead(IDModel):
    member_id: uuid.UUID
    achievement_id: uuid.UUID
    achievement: AchievementRead
    achieved_at: datetime
