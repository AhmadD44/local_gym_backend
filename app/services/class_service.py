"""Class booking. Capacity enforcement is race-condition-safe: we take a
row-level lock on the GymClass (`SELECT ... FOR UPDATE`) before counting
current bookings and inserting a new one, so two concurrent requests for
the last open seat cannot both succeed."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.enums import ClassBookingStatus
from app.models.gym_class import ClassBooking, GymClass


async def book_class(session: AsyncSession, *, class_id: uuid.UUID, member_id: uuid.UUID) -> ClassBooking:
    result = await session.execute(select(GymClass).where(GymClass.id == class_id).with_for_update())
    gym_class = result.scalar_one_or_none()
    if gym_class is None or not gym_class.is_active:
        raise NotFoundError("Class not found")
    if gym_class.start_time < datetime.now(UTC):
        raise BadRequestError("Cannot book a class that has already started")

    existing = await session.execute(
        select(ClassBooking).where(
            ClassBooking.class_id == class_id,
            ClassBooking.member_id == member_id,
            ClassBooking.status == ClassBookingStatus.BOOKED,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("You already have a booking for this class")

    count_result = await session.execute(
        select(func.count())
        .select_from(ClassBooking)
        .where(ClassBooking.class_id == class_id, ClassBooking.status == ClassBookingStatus.BOOKED)
    )
    booked_count = count_result.scalar_one()
    if booked_count >= gym_class.capacity:
        raise ConflictError("Class is fully booked")

    booking = ClassBooking(
        class_id=class_id, member_id=member_id, status=ClassBookingStatus.BOOKED, booked_at=datetime.now(UTC)
    )
    session.add(booking)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("You already have a booking for this class") from exc
    await session.refresh(booking)
    return booking


async def cancel_booking(session: AsyncSession, *, booking_id: uuid.UUID, member_id: uuid.UUID) -> ClassBooking:
    booking = await session.get(ClassBooking, booking_id)
    if booking is None or booking.member_id != member_id:
        raise NotFoundError("Booking not found")
    if booking.status != ClassBookingStatus.BOOKED:
        raise BadRequestError("Only an active booking can be cancelled")

    booking.status = ClassBookingStatus.CANCELLED
    booking.cancelled_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(booking)
    return booking


async def list_member_bookings(session: AsyncSession, *, member_id: uuid.UUID) -> list[ClassBooking]:
    result = await session.execute(
        select(ClassBooking).where(ClassBooking.member_id == member_id).order_by(ClassBooking.booked_at.desc())
    )
    return list(result.scalars().all())


async def get_booked_count(session: AsyncSession, *, class_id: uuid.UUID) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(ClassBooking)
        .where(ClassBooking.class_id == class_id, ClassBooking.status == ClassBookingStatus.BOOKED)
    )
    return result.scalar_one()
