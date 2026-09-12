import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.permissions import get_member_profile_for_user, require_admin, require_role
from app.models.enums import ClassBookingStatus, UserRole
from app.models.gym_class import ClassBooking, GymClass
from app.models.user import User
from app.schemas.gym_class import (
    ClassBookingAdminRead,
    ClassBookingRead,
    GymClassCreate,
    GymClassRead,
    GymClassUpdate,
)
from app.services import class_service

router = APIRouter(prefix="/classes", tags=["classes"])


async def _to_read(db: AsyncSession, gym_class: GymClass) -> GymClassRead:
    booked = await class_service.get_booked_count(db, class_id=gym_class.id)
    data = GymClassRead.model_validate(gym_class)
    data.booked_count = booked
    data.available_spots = max(gym_class.capacity - booked, 0)
    return data


@router.get("", response_model=list[GymClassRead], summary="List upcoming classes")
async def list_classes(
    db: AsyncSession = Depends(get_db),
    upcoming_only: bool = True,
    _=Depends(require_role(UserRole.MEMBER, UserRole.TRAINER, UserRole.ADMIN)),
):
    stmt = select(GymClass).where(GymClass.is_active.is_(True)).options(selectinload(GymClass.trainer))
    if upcoming_only:
        stmt = stmt.where(GymClass.start_time >= datetime.now(UTC))
    stmt = stmt.order_by(GymClass.start_time)
    result = await db.execute(stmt)
    classes = list(result.scalars().unique().all())
    return [await _to_read(db, c) for c in classes]


@router.post(
    "",
    response_model=GymClassRead,
    status_code=201,
    dependencies=[Depends(require_admin)],
    summary="Create a gym class (admin only)",
)
async def create_class(payload: GymClassCreate, db: AsyncSession = Depends(get_db)):
    gym_class = GymClass(**payload.model_dump())
    db.add(gym_class)
    await db.commit()
    result = await db.execute(
        select(GymClass).where(GymClass.id == gym_class.id).options(selectinload(GymClass.trainer))
    )
    return await _to_read(db, result.scalar_one())


@router.patch(
    "/{class_id}",
    response_model=GymClassRead,
    dependencies=[Depends(require_admin)],
    summary="Update a gym class (admin only)",
)
async def update_class(class_id: uuid.UUID, payload: GymClassUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(GymClass).where(GymClass.id == class_id).options(selectinload(GymClass.trainer))
    )
    gym_class = result.scalar_one_or_none()
    if gym_class is None:
        raise NotFoundError("Class not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(gym_class, field, value)
    await db.commit()
    await db.refresh(gym_class)
    return await _to_read(db, gym_class)


@router.get(
    "/{class_id}/bookings",
    response_model=list[ClassBookingAdminRead],
    dependencies=[Depends(require_admin)],
    summary="List a class's roster (admin only)",
    description="Who's booked into this class — the front-desk/check-in view. Not paginated: "
    "capacity is capped at 500, so a class's booking list is always bounded. Pass "
    "status_filter=BOOKED to see only active bookings (cancellations included by default).",
)
async def list_class_bookings(
    class_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    status_filter: ClassBookingStatus | None = None,
):
    gym_class = await db.get(GymClass, class_id)
    if gym_class is None:
        raise NotFoundError("Class not found")
    stmt = (
        select(ClassBooking)
        .where(ClassBooking.class_id == class_id)
        .options(selectinload(ClassBooking.member))
        .order_by(ClassBooking.booked_at)
    )
    if status_filter:
        stmt = stmt.where(ClassBooking.status == status_filter)
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())


@router.post(
    "/{class_id}/book",
    response_model=ClassBookingRead,
    status_code=201,
    summary="Book a class (member only, capacity is concurrency-safe)",
)
async def book_class(
    class_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(require_role(UserRole.MEMBER))
):
    profile = await get_member_profile_for_user(user, db)
    return await class_service.book_class(db, class_id=class_id, member_id=profile.id)


@router.post(
    "/bookings/{booking_id}/cancel",
    response_model=ClassBookingRead,
    summary="Cancel my class booking",
)
async def cancel_booking(
    booking_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(require_role(UserRole.MEMBER))
):
    profile = await get_member_profile_for_user(user, db)
    return await class_service.cancel_booking(db, booking_id=booking_id, member_id=profile.id)


@router.get("/bookings/me", response_model=list[ClassBookingRead], summary="List my bookings")
async def my_bookings(db: AsyncSession = Depends(get_db), user: User = Depends(require_role(UserRole.MEMBER))):
    profile = await get_member_profile_for_user(user, db)
    return await class_service.list_member_bookings(db, member_id=profile.id)
