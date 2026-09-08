import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import WorkoutSessionStatus


class WorkoutProgram(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "workout_programs"

    trainer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trainer_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("member_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    days: Mapped[list["WorkoutDay"]] = relationship(
        "WorkoutDay", back_populates="program", cascade="all, delete-orphan", order_by="WorkoutDay.day_number"
    )


class WorkoutDay(Base, UUIDPKMixin):
    __tablename__ = "workout_days"

    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workout_programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    program = relationship("WorkoutProgram", back_populates="days")
    exercises: Mapped[list["WorkoutExercise"]] = relationship(
        "WorkoutExercise",
        back_populates="workout_day",
        cascade="all, delete-orphan",
        order_by="WorkoutExercise.order_index",
    )


class WorkoutExercise(Base, UUIDPKMixin):
    __tablename__ = "workout_exercises"

    workout_day_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workout_days.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exercises.id", ondelete="RESTRICT"), nullable=False
    )
    sets: Mapped[int] = mapped_column(Integer, nullable=False)
    reps: Mapped[int] = mapped_column(Integer, nullable=False)
    target_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    rest_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    workout_day = relationship("WorkoutDay", back_populates="exercises")
    exercise = relationship("Exercise")


class WorkoutSession(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "workout_sessions"

    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workout_programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("member_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workout_day_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workout_days.id", ondelete="CASCADE"), nullable=False
    )
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[WorkoutSessionStatus] = mapped_column(
        Enum(WorkoutSessionStatus, name="workout_session_status", native_enum=True),
        default=WorkoutSessionStatus.SCHEDULED,
        nullable=False,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    workout_day = relationship("WorkoutDay")
    set_logs: Mapped[list["WorkoutSetLog"]] = relationship(
        "WorkoutSetLog", back_populates="session", cascade="all, delete-orphan"
    )


class WorkoutSetLog(Base, UUIDPKMixin):
    __tablename__ = "workout_set_logs"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workout_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workout_exercise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workout_exercises.id", ondelete="CASCADE"), nullable=False
    )
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    reps_done: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_used_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    session = relationship("WorkoutSession", back_populates="set_logs")
