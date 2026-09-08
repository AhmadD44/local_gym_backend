import uuid

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.permissions import get_current_active_user, require_role
from app.models.enums import UserRole
from app.models.exercise import Exercise
from app.schemas.exercise import ExerciseCreate, ExerciseRead, ExerciseUpdate
from app.utils.uploads import validate_and_store_image

router = APIRouter(prefix="/exercises", tags=["exercises"])

_MANAGE_EXERCISES = require_role(UserRole.ADMIN, UserRole.TRAINER)


@router.get("", response_model=list[ExerciseRead], summary="List exercises")
async def list_exercises(
    db: AsyncSession = Depends(get_db),
    muscle_group: str | None = None,
    active_only: bool = True,
    _=Depends(get_current_active_user),
):
    stmt = select(Exercise)
    if active_only:
        stmt = stmt.where(Exercise.is_active.is_(True))
    if muscle_group:
        stmt = stmt.where(Exercise.muscle_group == muscle_group)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post(
    "",
    response_model=ExerciseRead,
    status_code=201,
    dependencies=[Depends(_MANAGE_EXERCISES)],
    summary="Create an exercise",
)
async def create_exercise(payload: ExerciseCreate, db: AsyncSession = Depends(get_db)):
    exercise = Exercise(**payload.model_dump())
    db.add(exercise)
    await db.commit()
    await db.refresh(exercise)
    return exercise


@router.patch(
    "/{exercise_id}",
    response_model=ExerciseRead,
    dependencies=[Depends(_MANAGE_EXERCISES)],
    summary="Update an exercise",
)
async def update_exercise(exercise_id: uuid.UUID, payload: ExerciseUpdate, db: AsyncSession = Depends(get_db)):
    exercise = await db.get(Exercise, exercise_id)
    if exercise is None:
        raise NotFoundError("Exercise not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(exercise, field, value)
    await db.commit()
    await db.refresh(exercise)
    return exercise


@router.post(
    "/{exercise_id}/media",
    response_model=ExerciseRead,
    dependencies=[Depends(_MANAGE_EXERCISES)],
    summary="Upload exercise media (image)",
)
async def upload_exercise_media(exercise_id: uuid.UUID, file: UploadFile, db: AsyncSession = Depends(get_db)):
    exercise = await db.get(Exercise, exercise_id)
    if exercise is None:
        raise NotFoundError("Exercise not found")
    exercise.media_url = await validate_and_store_image(file, folder="exercise-media")
    await db.commit()
    await db.refresh(exercise)
    return exercise
