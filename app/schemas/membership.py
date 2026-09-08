import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from app.models.enums import MembershipStatus, PaymentStatus
from app.schemas.common import ORMModel, TimestampedModel


class MembershipPlanCreate(ORMModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    duration_days: int = Field(gt=0)
    price: Decimal = Field(gt=0)


class MembershipPlanUpdate(ORMModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    duration_days: int | None = Field(default=None, gt=0)
    price: Decimal | None = Field(default=None, gt=0)
    is_active: bool | None = None


class MembershipPlanRead(TimestampedModel):
    name: str
    description: str | None
    duration_days: int
    price: Decimal
    is_active: bool


class MembershipSubscribeRequest(ORMModel):
    plan_id: uuid.UUID


class MembershipConfirmPaymentRequest(ORMModel):
    notes: str | None = None


class MembershipExtendRequest(ORMModel):
    additional_days: int = Field(gt=0, le=730)


class MembershipSubscriptionRead(TimestampedModel):
    member_id: uuid.UUID
    plan_id: uuid.UUID
    plan: MembershipPlanRead
    status: MembershipStatus
    payment_status: PaymentStatus
    price_at_purchase: Decimal
    start_date: date | None
    expiry_date: date | None
    confirmed_by: uuid.UUID | None
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    notes: str | None
