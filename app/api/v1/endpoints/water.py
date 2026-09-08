from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import get_member_profile_for_user, require_role
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.tracking import WaterDaySummary, WaterEntryCreate, WaterEntryRead, WaterGoalRead, WaterGoalUpdate
from app.services import tracking_service

router = APIRouter(prefix="/water", tags=["water"])


@router.get("/goal", response_model=WaterGoalRead, summary="Get my water goal")
async def get_goal(db: AsyncSession = Depends(get_db), user: User = Depends(require_role(UserRole.MEMBER))):
    profile = await get_member_profile_for_user(user, db)
    return await tracking_service.get_or_create_water_goal(db, member_id=profile.id)


@router.put("/goal", response_model=WaterGoalRead, summary="Set my daily water goal")
async def set_goal(
    payload: WaterGoalUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.MEMBER)),
):
    profile = await get_member_profile_for_user(user, db)
    return await tracking_service.set_water_goal(db, member_id=profile.id, daily_target_ml=payload.daily_target_ml)


@router.post("/entries", response_model=WaterEntryRead, status_code=201, summary="Log a water entry")
async def add_entry(
    payload: WaterEntryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.MEMBER)),
):
    profile = await get_member_profile_for_user(user, db)
    return await tracking_service.add_water_entry(
        db, member_id=profile.id, amount_ml=payload.amount_ml, logged_at=payload.logged_at
    )


@router.get("/days/{day}", response_model=WaterDaySummary, summary="Get water intake for a given day")
async def get_day(
    day: date, db: AsyncSession = Depends(get_db), user: User = Depends(require_role(UserRole.MEMBER))
):
    profile = await get_member_profile_for_user(user, db)
    entries = await tracking_service.get_water_day(db, member_id=profile.id, day=day)
    goal = await tracking_service.get_or_create_water_goal(db, member_id=profile.id)
    return WaterDaySummary(
        day=day,
        total_ml=sum(e.amount_ml for e in entries),
        goal_ml=goal.daily_target_ml,
        entries=[WaterEntryRead.model_validate(e) for e in entries],
    )
