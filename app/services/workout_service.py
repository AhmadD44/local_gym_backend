import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.enums import WorkoutSessionStatus
from app.models.workout import (
    WorkoutDay,
    WorkoutExercise,
    WorkoutProgram,
    WorkoutSession,
    WorkoutSetLog,
)
from app.schemas.workout import WorkoutProgramCreate, WorkoutSessionComplete


def _program_load_options():
    return (
        selectinload(WorkoutProgram.days)
        .selectinload(WorkoutDay.exercises)
        .selectinload(WorkoutExercise.exercise),
    )


async def create_program(
    session: AsyncSession, *, trainer_id: uuid.UUID, data: WorkoutProgramCreate
) -> WorkoutProgram:
    program = WorkoutProgram(
        trainer_id=trainer_id,
        member_id=data.member_id,
        name=data.name,
        description=data.description,
        start_date=data.start_date,
        end_date=data.end_date,
    )
    for day_in in data.days:
        day = WorkoutDay(day_number=day_in.day_number, name=day_in.name)
        for idx, ex_in in enumerate(day_in.exercises):
            day.exercises.append(
                WorkoutExercise(
                    exercise_id=ex_in.exercise_id,
                    sets=ex_in.sets,
                    reps=ex_in.reps,
                    target_weight_kg=ex_in.target_weight_kg,
                    rest_seconds=ex_in.rest_seconds,
                    notes=ex_in.notes,
                    order_index=ex_in.order_index or idx,
                )
            )
        program.days.append(day)

    session.add(program)
    await session.commit()

    result = await session.execute(
        select(WorkoutProgram).where(WorkoutProgram.id == program.id).options(*_program_load_options())
    )
    return result.scalar_one()


async def get_program_detail(session: AsyncSession, *, program_id: uuid.UUID) -> WorkoutProgram:
    result = await session.execute(
        select(WorkoutProgram).where(WorkoutProgram.id == program_id).options(*_program_load_options())
    )
    program = result.scalar_one_or_none()
    if program is None:
        raise NotFoundError("Workout program not found")
    return program


async def list_programs_for_member(session: AsyncSession, *, member_id: uuid.UUID) -> list[WorkoutProgram]:
    result = await session.execute(
        select(WorkoutProgram)
        .where(WorkoutProgram.member_id == member_id)
        .order_by(WorkoutProgram.created_at.desc())
    )
    return list(result.scalars().unique().all())


async def schedule_session(
    session: AsyncSession, *, program: WorkoutProgram, workout_day_id: uuid.UUID, scheduled_date
) -> WorkoutSession:
    day = await session.get(WorkoutDay, workout_day_id)
    if day is None or day.program_id != program.id:
        raise BadRequestError("Workout day does not belong to this program")

    ws = WorkoutSession(
        program_id=program.id,
        member_id=program.member_id,
        workout_day_id=workout_day_id,
        scheduled_date=scheduled_date,
        status=WorkoutSessionStatus.SCHEDULED,
    )
    session.add(ws)
    await session.commit()
    await session.refresh(ws)
    return ws


async def get_owned_session(
    session: AsyncSession, *, session_id: uuid.UUID, member_id: uuid.UUID
) -> WorkoutSession:
    result = await session.execute(
        select(WorkoutSession)
        .where(WorkoutSession.id == session_id)
        .options(selectinload(WorkoutSession.set_logs))
    )
    ws = result.scalar_one_or_none()
    if ws is None:
        raise NotFoundError("Workout session not found")
    if ws.member_id != member_id:
        raise NotFoundError("Workout session not found")
    return ws


async def complete_session(
    session: AsyncSession, *, workout_session: WorkoutSession, data: WorkoutSessionComplete
) -> WorkoutSession:
    if workout_session.status == WorkoutSessionStatus.COMPLETED:
        raise BadRequestError("Session already completed")

    valid_exercise_ids = set(
        (
            await session.execute(
                select(WorkoutExercise.id).where(WorkoutExercise.workout_day_id == workout_session.workout_day_id)
            )
        )
        .scalars()
        .all()
    )
    for log_in in data.set_logs:
        if log_in.workout_exercise_id not in valid_exercise_ids:
            raise BadRequestError("workout_exercise_id does not belong to this session's workout day")
        session.add(
            WorkoutSetLog(
                session_id=workout_session.id,
                workout_exercise_id=log_in.workout_exercise_id,
                set_number=log_in.set_number,
                reps_done=log_in.reps_done,
                weight_used_kg=log_in.weight_used_kg,
                completed=log_in.completed,
            )
        )
    workout_session.status = WorkoutSessionStatus.COMPLETED
    workout_session.completed_at = datetime.now(UTC)
    workout_session.notes = data.notes
    await session.commit()
    await session.refresh(workout_session)
    return workout_session
