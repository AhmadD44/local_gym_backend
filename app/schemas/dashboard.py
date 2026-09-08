import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import MembershipStatus
from app.schemas.gym_class import GymClassRead
from app.schemas.promotion import PromotionRead
from app.schemas.workout import WorkoutSessionRead


class MembershipStatusSummary(BaseModel):
    has_membership: bool
    status: MembershipStatus | None = None
    plan_name: str | None = None
    expiry_date: date | None = None
    days_remaining: int | None = None


class ProgressSummary(BaseModel):
    latest_weight_kg: float | None = None
    weight_change_kg: float | None = None
    total_workouts_completed: int = 0
    personal_records_count: int = 0


class MemberDashboardResponse(BaseModel):
    membership: MembershipStatusSummary
    todays_workout: WorkoutSessionRead | None
    upcoming_classes: list[GymClassRead]
    active_promotions: list[PromotionRead]
    progress: ProgressSummary


class DigitalMemberCard(BaseModel):
    member_id: uuid.UUID
    member_code: str
    full_name: str
    photo_url: str | None
    membership_status: MembershipStatus | None
    membership_expiry: date | None


class AdminDashboardResponse(BaseModel):
    total_members: int
    active_memberships: int
    expiring_memberships_7d: int
    pending_payments: int
    active_classes: int
    bookings_today: int
    pending_orders: int
    revenue_month: Decimal
    active_promotions: int
    total_trainers: int
