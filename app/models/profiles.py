import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import FitnessLevel


class MemberProfile(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "member_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    fitness_level: Mapped[FitnessLevel | None] = mapped_column(
        Enum(FitnessLevel, name="fitness_level", native_enum=True), nullable=True
    )
    fitness_goal: Mapped[str | None] = mapped_column(String(500), nullable=True)
    member_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    user = relationship("User", back_populates="member_profile")


class TrainerProfile(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "trainer_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    specialization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    years_experience: Mapped[int | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="trainer_profile")


class TrainerMemberAssignment(Base, UUIDPKMixin):
    __tablename__ = "trainer_member_assignments"

    trainer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trainer_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("member_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    unassigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "uq_active_assignment_per_member",
            "member_id",
            unique=True,
            postgresql_where="active = true",
        ),
    )
