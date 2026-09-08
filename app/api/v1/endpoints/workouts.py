import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.permissions import (
    get_accessible_member_profile,
    get_current_active_user,
    get_member_profile_for_user,
    get_trainer_profile_for_user,
    is_member_assigned_to_trainer,
    require_role,
)
from app.models.enums import UserRole
from app.models.user import User
from app.models.workout import WorkoutDay, WorkoutProgram
from app.schemas.workout import (
    WorkoutProgramCreate,
    WorkoutProgramRead,
    WorkoutProgramSummary,
    WorkoutSessionComplete,
    WorkoutSessionCreate,
    WorkoutSessionRead,
)
from app.services import workout_service

router = APIRouter(prefix="/workouts", tags=["workouts"])


async def _assert_program_access(db: AsyncSession, program: WorkoutProgram, user: User) -> None:
    if user.role == UserRole.ADMIN:
        return
    if user.role == UserRole.TRAINER:
        trainer = await get_trainer_profile_for_user(user, db)
        if program.trainer_id == trainer.id:
            return
    if user.role == UserRole.MEMBER:
        member = await get_member_profile_for_user(user, db)
        if program.member_id == member.id:
            return
    raise NotFoundError("Workout program not found")


@router.post(
    "/programs",
    response_model=WorkoutProgramRead,
    status_code=201,
    summary="Create a workout program for an assigned member (trainer only)",
)
async def create_program(
    payload: WorkoutProgramCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.TRAINER)),
):
    trainer = await get_trainer_profile_for_user(user, db)
    if not await is_member_assigned_to_trainer(db, trainer_id=trainer.id, member_id=payload.member_id):
        raise ForbiddenError("You may only create programs for members assigned to you")
    return await workout_service.create_program(db, trainer_id=trainer.id, data=payload)


@router.get("/programs/{program_id}", response_model=WorkoutProgramRead, summary="Get a workout program")
async def get_program(
    program_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_active_user)
):
    program = await workout_service.get_program_detail(db, program_id=program_id)
    await _assert_program_access(db, program, user)
    return program


@router.get(
    "/programs/me",
    response_model=list[WorkoutProgramSummary],
    summary="List my workout programs (member)",
)
async def list_my_programs(
    db: AsyncSession = Depends(get_db), user: User = Depends(require_role(UserRole.MEMBER))
):
    member = await get_member_profile_for_user(user, db)
    return await workout_service.list_programs_for_member(db, member_id=member.id)


@router.get(
    "/members/{member_id}/programs",
    response_model=list[WorkoutProgramSummary],
    summary="List a member's workout programs (trainer/admin, ownership-checked)",
)
async def list_member_programs(
    member_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.TRAINER, UserRole.ADMIN)),
):
    member = await get_accessible_member_profile(member_id, current_user=user, db=db)
    return await workout_service.list_programs_for_member(db, member_id=member.id)


@router.post(
    "/sessions",
    response_model=WorkoutSessionRead,
    status_code=201,
    summary="Schedule a workout session from a program day (member)",
)
async def schedule_session(
    payload: WorkoutSessionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.MEMBER)),
):
    member = await get_member_profile_for_user(user, db)
    # Confirm the workout day belongs to a program owned by this member.
    result = await db.execute(select(WorkoutDay).where(WorkoutDay.id == payload.workout_day_id))
    day = result.scalar_one_or_none()
    if day is None:
        raise NotFoundError("Workout day not found")
    program = await workout_service.get_program_detail(db, program_id=day.program_id)
    if program.member_id != member.id:
        raise NotFoundError("Workout day not found")

    return await workout_service.schedule_session(
        db, program=program, workout_day_id=payload.workout_day_id, scheduled_date=payload.scheduled_date
    )


@router.get(
    "/sessions/{session_id}",
    response_model=WorkoutSessionRead,
    summary="Get a workout session (member, own only)",
)
async def get_session(
    session_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(require_role(UserRole.MEMBER))
):
    member = await get_member_profile_for_user(user, db)
    return await workout_service.get_owned_session(db, session_id=session_id, member_id=member.id)


@router.post(
    "/sessions/{session_id}/complete",
    response_model=WorkoutSessionRead,
    summary="Complete a workout session with set logs (member, own only)",
)
async def complete_session(
    session_id: uuid.UUID,
    payload: WorkoutSessionComplete,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.MEMBER)),
):
    member = await get_member_profile_for_user(user, db)
    workout_session = await workout_service.get_owned_session(db, session_id=session_id, member_id=member.id)
    return await workout_service.complete_session(db, workout_session=workout_session, data=payload)
