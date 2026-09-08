from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import get_member_profile_for_user, require_role
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.tracking import (
    MealEntryCreate,
    MealEntryRead,
    NutritionDaySummary,
    NutritionGoalRead,
    NutritionGoalUpdate,
)
from app.services import tracking_service

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


@router.get("/goal", response_model=NutritionGoalRead, summary="Get my nutrition goal")
async def get_goal(db: AsyncSession = Depends(get_db), user: User = Depends(require_role(UserRole.MEMBER))):
    profile = await get_member_profile_for_user(user, db)
    return await tracking_service.get_or_create_nutrition_goal(db, member_id=profile.id)


@router.put("/goal", response_model=NutritionGoalRead, summary="Set my nutrition goal")
async def set_goal(
    payload: NutritionGoalUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.MEMBER)),
):
    profile = await get_member_profile_for_user(user, db)
    return await tracking_service.set_nutrition_goal(db, member_id=profile.id, **payload.model_dump())


@router.post("/meals", response_model=MealEntryRead, status_code=201, summary="Log a meal entry")
async def add_meal(
    payload: MealEntryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.MEMBER)),
):
    profile = await get_member_profile_for_user(user, db)
    return await tracking_service.add_meal_entry(db, member_id=profile.id, **payload.model_dump())


@router.get("/days/{day}", response_model=NutritionDaySummary, summary="Get nutrition intake for a given day")
async def get_day(
    day: date, db: AsyncSession = Depends(get_db), user: User = Depends(require_role(UserRole.MEMBER))
):
    profile = await get_member_profile_for_user(user, db)
    entries = await tracking_service.get_meals_day(db, member_id=profile.id, day=day)
    return NutritionDaySummary(
        day=day,
        total_calories=sum(e.calories or 0 for e in entries),
        total_protein_g=sum(e.protein_g or 0 for e in entries),
        total_carbs_g=sum(e.carbs_g or 0 for e in entries),
        total_fat_g=sum(e.fat_g or 0 for e in entries),
        entries=[MealEntryRead.model_validate(e) for e in entries],
    )
