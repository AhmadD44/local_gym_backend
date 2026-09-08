import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import WorkoutSessionStatus
from app.schemas.common import IDModel, TimestampedModel
from app.schemas.exercise import ExerciseRead


class WorkoutExerciseCreate(BaseModel):
    exercise_id: uuid.UUID
    sets: int = Field(gt=0, le=50)
    reps: int = Field(gt=0, le=200)
    target_weight_kg: float | None = Field(default=None, ge=0)
    rest_seconds: int | None = Field(default=None, ge=0, le=3600)
    notes: str | None = None
    order_index: int = 0


class WorkoutExerciseRead(IDModel):
    exercise_id: uuid.UUID
    exercise: ExerciseRead
    sets: int
    reps: int
    target_weight_kg: float | None
    rest_seconds: int | None
    notes: str | None
    order_index: int


class WorkoutDayCreate(BaseModel):
    day_number: int = Field(ge=1, le=14)
    name: str = Field(min_length=1, max_length=150)
    exercises: list[WorkoutExerciseCreate] = Field(default_factory=list)


class WorkoutDayRead(IDModel):
    day_number: int
    name: str
    exercises: list[WorkoutExerciseRead]


class WorkoutProgramCreate(BaseModel):
    member_id: uuid.UUID
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    days: list[WorkoutDayCreate] = Field(default_factory=list)


class WorkoutProgramUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool | None = None


class WorkoutProgramRead(TimestampedModel):
    trainer_id: uuid.UUID
    member_id: uuid.UUID
    name: str
    description: str | None
    start_date: date | None
    end_date: date | None
    is_active: bool
    days: list[WorkoutDayRead]


class WorkoutProgramSummary(TimestampedModel):
    trainer_id: uuid.UUID
    member_id: uuid.UUID
    name: str
    description: str | None
    start_date: date | None
    end_date: date | None
    is_active: bool


class WorkoutSessionCreate(BaseModel):
    workout_day_id: uuid.UUID
    scheduled_date: date


class SetLogUpdate(BaseModel):
    workout_exercise_id: uuid.UUID
    set_number: int = Field(ge=1)
    reps_done: int | None = Field(default=None, ge=0)
    weight_used_kg: float | None = Field(default=None, ge=0)
    completed: bool = True


class WorkoutSessionComplete(BaseModel):
    set_logs: list[SetLogUpdate]
    notes: str | None = None


class WorkoutSetLogRead(IDModel):
    workout_exercise_id: uuid.UUID
    set_number: int
    reps_done: int | None
    weight_used_kg: float | None
    completed: bool


class WorkoutSessionRead(TimestampedModel):
    program_id: uuid.UUID
    member_id: uuid.UUID
    workout_day_id: uuid.UUID
    scheduled_date: date
    completed_at: datetime | None
    status: WorkoutSessionStatus
    notes: str | None
    set_logs: list[WorkoutSetLogRead]
