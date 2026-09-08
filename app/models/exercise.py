from sqlalchemy import Boolean, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import DifficultyLevel


class Exercise(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "exercises"

    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    muscle_group: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    equipment: Mapped[str | None] = mapped_column(String(150), nullable=True)
    difficulty: Mapped[DifficultyLevel | None] = mapped_column(
        Enum(DifficultyLevel, name="difficulty_level", native_enum=True), nullable=True
    )
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
