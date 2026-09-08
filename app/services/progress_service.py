import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.progress import Achievement, BodyMeasurement, MemberAchievement, PersonalRecord, ProgressPhoto
from app.schemas.progress import BodyMeasurementCreate, PersonalRecordCreate, ProgressPhotoCreate


async def add_body_measurement(
    session: AsyncSession, *, member_id: uuid.UUID, data: BodyMeasurementCreate, recorded_by: uuid.UUID
) -> BodyMeasurement:
    measurement = BodyMeasurement(member_id=member_id, recorded_by=recorded_by, **data.model_dump())
    session.add(measurement)
    await session.commit()
    await session.refresh(measurement)
    return measurement


async def list_body_measurements(session: AsyncSession, *, member_id: uuid.UUID) -> list[BodyMeasurement]:
    result = await session.execute(
        select(BodyMeasurement)
        .where(BodyMeasurement.member_id == member_id)
        .order_by(BodyMeasurement.recorded_at.desc())
    )
    return list(result.scalars().all())


async def add_progress_photo(
    session: AsyncSession, *, member_id: uuid.UUID, data: ProgressPhotoCreate
) -> ProgressPhoto:
    photo = ProgressPhoto(member_id=member_id, **data.model_dump())
    session.add(photo)
    await session.commit()
    await session.refresh(photo)
    return photo


async def list_progress_photos(session: AsyncSession, *, member_id: uuid.UUID) -> list[ProgressPhoto]:
    result = await session.execute(
        select(ProgressPhoto).where(ProgressPhoto.member_id == member_id).order_by(ProgressPhoto.taken_at.desc())
    )
    return list(result.scalars().all())


async def add_personal_record(
    session: AsyncSession, *, member_id: uuid.UUID, data: PersonalRecordCreate
) -> PersonalRecord:
    record = PersonalRecord(member_id=member_id, **data.model_dump())
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def list_personal_records(session: AsyncSession, *, member_id: uuid.UUID) -> list[PersonalRecord]:
    result = await session.execute(
        select(PersonalRecord)
        .where(PersonalRecord.member_id == member_id)
        .order_by(PersonalRecord.achieved_at.desc())
    )
    return list(result.scalars().all())


async def grant_achievement(
    session: AsyncSession, *, member_id: uuid.UUID, achievement_id: uuid.UUID
) -> MemberAchievement:
    achievement = await session.get(Achievement, achievement_id)
    if achievement is None:
        raise NotFoundError("Achievement not found")
    existing = await session.execute(
        select(MemberAchievement).where(
            MemberAchievement.member_id == member_id, MemberAchievement.achievement_id == achievement_id
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("Member already has this achievement")

    grant = MemberAchievement(member_id=member_id, achievement_id=achievement_id, achieved_at=datetime.now(UTC))
    session.add(grant)
    await session.commit()
    await session.refresh(grant)
    return grant


async def list_member_achievements(session: AsyncSession, *, member_id: uuid.UUID) -> list[MemberAchievement]:
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(MemberAchievement)
        .where(MemberAchievement.member_id == member_id)
        .options(selectinload(MemberAchievement.achievement))
    )
    return list(result.scalars().all())
