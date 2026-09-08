import uuid
from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import ContactStatus
from app.schemas.common import IDModel


class GymSettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    description: str | None
    phone: str | None
    email: str | None
    address: str | None
    logo_url: str | None


class GymSettingsUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    address: str | None = None
    logo_url: str | None = None


class OpeningHoursUpdate(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    open_time: time | None = None
    close_time: time | None = None
    is_closed: bool = False


class OpeningHoursRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    day_of_week: int
    open_time: time | None
    close_time: time | None
    is_closed: bool


class GymRuleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    order_index: int = 0


class GymRuleRead(IDModel):
    title: str
    description: str
    order_index: int


class FAQCreate(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    answer: str = Field(min_length=1)
    order_index: int = 0


class FAQUpdate(BaseModel):
    question: str | None = Field(default=None, min_length=1, max_length=500)
    answer: str | None = None
    order_index: int | None = None
    is_active: bool | None = None


class FAQRead(IDModel):
    question: str
    answer: str
    order_index: int
    is_active: bool


class ContactRequestCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1)


class ContactRequestRead(IDModel):
    name: str
    email: str
    phone: str | None
    subject: str
    message: str
    status: ContactStatus
    created_at: datetime


class ContactRequestStatusUpdate(BaseModel):
    status: ContactStatus


class FeedbackCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class FeedbackRead(IDModel):
    member_id: uuid.UUID
    rating: int
    comment: str | None
    created_at: datetime
