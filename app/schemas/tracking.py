import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MealType
from app.schemas.common import IDModel


class WaterGoalUpdate(BaseModel):
    daily_target_ml: int = Field(gt=0, le=10000)


class WaterGoalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    member_id: uuid.UUID
    daily_target_ml: int


class WaterEntryCreate(BaseModel):
    amount_ml: int = Field(gt=0, le=5000)
    logged_at: datetime | None = None


class WaterEntryRead(IDModel):
    member_id: uuid.UUID
    amount_ml: int
    logged_at: datetime


class WaterDaySummary(BaseModel):
    day: date
    total_ml: int
    goal_ml: int
    entries: list[WaterEntryRead]


class NutritionGoalUpdate(BaseModel):
    daily_calories: float | None = Field(default=None, gt=0)
    protein_g: float | None = Field(default=None, ge=0)
    carbs_g: float | None = Field(default=None, ge=0)
    fat_g: float | None = Field(default=None, ge=0)


class NutritionGoalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    member_id: uuid.UUID
    daily_calories: float | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None


class MealEntryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    meal_type: MealType
    calories: float | None = Field(default=None, ge=0)
    protein_g: float | None = Field(default=None, ge=0)
    carbs_g: float | None = Field(default=None, ge=0)
    fat_g: float | None = Field(default=None, ge=0)
    logged_at: datetime | None = None


class MealEntryRead(IDModel):
    member_id: uuid.UUID
    name: str
    meal_type: MealType
    calories: float | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None
    logged_at: datetime


class NutritionDaySummary(BaseModel):
    day: date
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    entries: list[MealEntryRead]
