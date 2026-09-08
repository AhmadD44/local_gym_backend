import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import ClassBookingStatus


class GymClass(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "gym_classes"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    trainer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trainer_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[str | None] = mapped_column(String(150), nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    trainer = relationship("TrainerProfile")


class ClassBooking(Base, UUIDPKMixin):
    __tablename__ = "class_bookings"

    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gym_classes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("member_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ClassBookingStatus] = mapped_column(
        Enum(ClassBookingStatus, name="class_booking_status", native_enum=True),
        default=ClassBookingStatus.BOOKED,
        nullable=False,
    )
    booked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    gym_class = relationship("GymClass")

    __table_args__ = (
        Index(
            "uq_one_active_booking_per_member",
            "class_id",
            "member_id",
            unique=True,
            postgresql_where="status = 'BOOKED'",
        ),
    )
