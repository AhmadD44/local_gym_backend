import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import MembershipStatus, PaymentStatus


class MembershipPlan(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "membership_plans"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_days: Mapped[int] = mapped_column(nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)


class MembershipSubscription(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "membership_subscriptions"

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("member_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("membership_plans.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[MembershipStatus] = mapped_column(
        Enum(MembershipStatus, name="membership_status", native_enum=True),
        nullable=False,
        default=MembershipStatus.PENDING,
        index=True,
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", native_enum=True),
        nullable=False,
        default=PaymentStatus.PENDING,
        index=True,
    )
    price_at_purchase: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    plan = relationship("MembershipPlan")
    member = relationship("MemberProfile")

    __table_args__ = (
        # A member may only have one PENDING/ACTIVE subscription at a time.
        # Enforced at the DB level (not just in service code) so a race
        # between two concurrent "subscribe" requests can't both succeed.
        Index(
            "uq_one_open_subscription_per_member",
            "member_id",
            unique=True,
            postgresql_where="status IN ('PENDING', 'ACTIVE')",
        ),
    )
