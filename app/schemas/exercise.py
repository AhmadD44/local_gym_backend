from pydantic import BaseModel, Field

from app.models.enums import DifficultyLevel
from app.schemas.common import TimestampedModel


class ExerciseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    muscle_group: str | None = Field(default=None, max_length=100)
    equipment: str | None = Field(default=None, max_length=150)
    difficulty: DifficultyLevel | None = None
    instructions: str | None = None
    media_url: str | None = Field(default=None, max_length=500)


class ExerciseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    muscle_group: str | None = Field(default=None, max_length=100)
    equipment: str | None = Field(default=None, max_length=150)
    difficulty: DifficultyLevel | None = None
    instructions: str | None = None
    media_url: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class ExerciseRead(TimestampedModel):
    name: str
    description: str | None
    muscle_group: str | None
    equipment: str | None
    difficulty: DifficultyLevel | None
    instructions: str | None
    media_url: str | None
    is_active: bool
