import uuid
from datetime import UTC, date, datetime, time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tracking import MealEntry, NutritionGoal, WaterEntry, WaterGoal


async def get_or_create_water_goal(session: AsyncSession, *, member_id: uuid.UUID) -> WaterGoal:
    result = await session.execute(select(WaterGoal).where(WaterGoal.member_id == member_id))
    goal = result.scalar_one_or_none()
    if goal is None:
        goal = WaterGoal(member_id=member_id, daily_target_ml=2000)
        session.add(goal)
        await session.commit()
        await session.refresh(goal)
    return goal


async def set_water_goal(session: AsyncSession, *, member_id: uuid.UUID, daily_target_ml: int) -> WaterGoal:
    goal = await get_or_create_water_goal(session, member_id=member_id)
    goal.daily_target_ml = daily_target_ml
    await session.commit()
    await session.refresh(goal)
    return goal


async def add_water_entry(
    session: AsyncSession, *, member_id: uuid.UUID, amount_ml: int, logged_at: datetime | None
) -> WaterEntry:
    entry = WaterEntry(member_id=member_id, amount_ml=amount_ml, logged_at=logged_at or datetime.now(UTC))
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def get_water_day(session: AsyncSession, *, member_id: uuid.UUID, day: date) -> list[WaterEntry]:
    start = datetime.combine(day, time.min, tzinfo=UTC)
    end = datetime.combine(day, time.max, tzinfo=UTC)
    result = await session.execute(
        select(WaterEntry)
        .where(WaterEntry.member_id == member_id, WaterEntry.logged_at >= start, WaterEntry.logged_at <= end)
        .order_by(WaterEntry.logged_at)
    )
    return list(result.scalars().all())


async def get_or_create_nutrition_goal(session: AsyncSession, *, member_id: uuid.UUID) -> NutritionGoal:
    result = await session.execute(select(NutritionGoal).where(NutritionGoal.member_id == member_id))
    goal = result.scalar_one_or_none()
    if goal is None:
        goal = NutritionGoal(member_id=member_id)
        session.add(goal)
        await session.commit()
        await session.refresh(goal)
    return goal


async def set_nutrition_goal(session: AsyncSession, *, member_id: uuid.UUID, **fields) -> NutritionGoal:
    goal = await get_or_create_nutrition_goal(session, member_id=member_id)
    for key, value in fields.items():
        if value is not None:
            setattr(goal, key, value)
    await session.commit()
    await session.refresh(goal)
    return goal


async def add_meal_entry(session: AsyncSession, *, member_id: uuid.UUID, **fields) -> MealEntry:
    fields.setdefault("logged_at", datetime.now(UTC))
    if fields.get("logged_at") is None:
        fields["logged_at"] = datetime.now(UTC)
    entry = MealEntry(member_id=member_id, **fields)
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def get_meals_day(session: AsyncSession, *, member_id: uuid.UUID, day: date) -> list[MealEntry]:
    start = datetime.combine(day, time.min, tzinfo=UTC)
    end = datetime.combine(day, time.max, tzinfo=UTC)
    result = await session.execute(
        select(MealEntry)
        .where(MealEntry.member_id == member_id, MealEntry.logged_at >= start, MealEntry.logged_at <= end)
        .order_by(MealEntry.logged_at)
    )
    return list(result.scalars().all())
