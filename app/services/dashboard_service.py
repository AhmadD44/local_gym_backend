import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import (
    ClassBookingStatus,
    MembershipStatus,
    OrderStatus,
    PaymentStatus,
    WorkoutSessionStatus,
)
from app.models.gym_class import ClassBooking, GymClass
from app.models.membership import MembershipSubscription
from app.models.profiles import MemberProfile, TrainerProfile
from app.models.progress import BodyMeasurement, PersonalRecord
from app.models.store import StoreOrder
from app.models.workout import WorkoutSession
from app.schemas.dashboard import (
    AdminDashboardResponse,
    DigitalMemberCard,
    MemberDashboardResponse,
    MembershipStatusSummary,
    ProgressSummary,
)
from app.schemas.workout import WorkoutSessionRead
from app.services.promotion_service import list_active_promotions, promotion_to_read


async def get_membership_status_summary(session: AsyncSession, *, member_id: uuid.UUID) -> MembershipStatusSummary:
    result = await session.execute(
        select(MembershipSubscription)
        .where(MembershipSubscription.member_id == member_id)
        .options(selectinload(MembershipSubscription.plan))
        .order_by(MembershipSubscription.created_at.desc())
    )
    subscription = result.scalars().first()
    if subscription is None:
        return MembershipStatusSummary(has_membership=False)

    days_remaining = None
    if subscription.expiry_date:
        days_remaining = max((subscription.expiry_date - date.today()).days, 0)

    return MembershipStatusSummary(
        has_membership=True,
        status=subscription.status,
        plan_name=subscription.plan.name if subscription.plan else None,
        expiry_date=subscription.expiry_date,
        days_remaining=days_remaining,
    )


async def get_digital_member_card(session: AsyncSession, *, member: MemberProfile) -> DigitalMemberCard:
    summary = await get_membership_status_summary(session, member_id=member.id)
    return DigitalMemberCard(
        member_id=member.id,
        member_code=member.member_code,
        full_name=member.full_name,
        photo_url=member.photo_url,
        membership_status=summary.status,
        membership_expiry=summary.expiry_date,
    )


async def get_member_dashboard(session: AsyncSession, *, member_id: uuid.UUID) -> MemberDashboardResponse:
    membership = await get_membership_status_summary(session, member_id=member_id)

    today = date.today()
    session_result = await session.execute(
        select(WorkoutSession)
        .where(
            WorkoutSession.member_id == member_id,
            WorkoutSession.scheduled_date == today,
            WorkoutSession.status == WorkoutSessionStatus.SCHEDULED,
        )
        .options(selectinload(WorkoutSession.set_logs))
        .limit(1)
    )
    todays_workout = session_result.scalars().first()

    now = datetime.now(UTC)
    upcoming_result = await session.execute(
        select(GymClass)
        .join(ClassBooking, ClassBooking.class_id == GymClass.id)
        .where(
            ClassBooking.member_id == member_id,
            ClassBooking.status == ClassBookingStatus.BOOKED,
            GymClass.start_time >= now,
        )
        .options(selectinload(GymClass.trainer))
        .order_by(GymClass.start_time)
        .limit(5)
    )
    upcoming_classes = list(upcoming_result.scalars().unique().all())

    promotions = [promotion_to_read(p) for p in await list_active_promotions(session)]

    measurement_result = await session.execute(
        select(BodyMeasurement)
        .where(BodyMeasurement.member_id == member_id)
        .order_by(BodyMeasurement.recorded_at.desc())
        .limit(2)
    )
    recent_measurements = list(measurement_result.scalars().all())
    latest_weight = recent_measurements[0].weight_kg if recent_measurements else None
    weight_change = None
    if len(recent_measurements) == 2 and recent_measurements[0].weight_kg and recent_measurements[1].weight_kg:
        weight_change = recent_measurements[0].weight_kg - recent_measurements[1].weight_kg

    completed_count_result = await session.execute(
        select(func.count())
        .select_from(WorkoutSession)
        .where(WorkoutSession.member_id == member_id, WorkoutSession.status == WorkoutSessionStatus.COMPLETED)
    )
    pr_count_result = await session.execute(
        select(func.count()).select_from(PersonalRecord).where(PersonalRecord.member_id == member_id)
    )

    return MemberDashboardResponse(
        membership=membership,
        todays_workout=WorkoutSessionRead.model_validate(todays_workout) if todays_workout else None,
        upcoming_classes=[_class_read_with_counts(c, booked_count=0) for c in upcoming_classes],
        active_promotions=promotions,
        progress=ProgressSummary(
            latest_weight_kg=latest_weight,
            weight_change_kg=weight_change,
            total_workouts_completed=completed_count_result.scalar_one(),
            personal_records_count=pr_count_result.scalar_one(),
        ),
    )


def _class_read_with_counts(gym_class: GymClass, *, booked_count: int):
    from app.schemas.gym_class import GymClassRead

    data = GymClassRead.model_validate(gym_class)
    data.booked_count = booked_count
    data.available_spots = max(gym_class.capacity - booked_count, 0)
    return data


async def get_admin_dashboard(session: AsyncSession) -> AdminDashboardResponse:
    now = datetime.now(UTC)
    week_from_now = date.today() + timedelta(days=7)
    month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_members = (await session.execute(select(func.count()).select_from(MemberProfile))).scalar_one()
    active_memberships = (
        await session.execute(
            select(func.count())
            .select_from(MembershipSubscription)
            .where(MembershipSubscription.status == MembershipStatus.ACTIVE)
        )
    ).scalar_one()
    expiring_soon = (
        await session.execute(
            select(func.count())
            .select_from(MembershipSubscription)
            .where(
                MembershipSubscription.status == MembershipStatus.ACTIVE,
                MembershipSubscription.expiry_date <= week_from_now,
            )
        )
    ).scalar_one()
    pending_payments = (
        await session.execute(
            select(func.count())
            .select_from(MembershipSubscription)
            .where(MembershipSubscription.payment_status == PaymentStatus.PENDING)
        )
    ).scalar_one()
    active_classes = (
        await session.execute(
            select(func.count())
            .select_from(GymClass)
            .where(GymClass.is_active.is_(True), GymClass.start_time >= now)
        )
    ).scalar_one()
    bookings_today = (
        await session.execute(
            select(func.count())
            .select_from(ClassBooking)
            .join(GymClass, GymClass.id == ClassBooking.class_id)
            .where(
                func.date(GymClass.start_time) == date.today(), ClassBooking.status == ClassBookingStatus.BOOKED
            )
        )
    ).scalar_one()
    pending_orders = (
        await session.execute(
            select(func.count())
            .select_from(StoreOrder)
            .where(StoreOrder.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PREPARING]))
        )
    ).scalar_one()
    revenue_month = (
        await session.execute(
            select(func.coalesce(func.sum(StoreOrder.total), 0)).where(
                StoreOrder.payment_status == PaymentStatus.PAID, StoreOrder.created_at >= month_start
            )
        )
    ).scalar_one()
    active_promotions_count = len(await list_active_promotions(session))
    total_trainers = (await session.execute(select(func.count()).select_from(TrainerProfile))).scalar_one()

    return AdminDashboardResponse(
        total_members=total_members,
        active_memberships=active_memberships,
        expiring_memberships_7d=expiring_soon,
        pending_payments=pending_payments,
        active_classes=active_classes,
        bookings_today=bookings_today,
        pending_orders=pending_orders,
        revenue_month=Decimal(revenue_month),
        active_promotions=active_promotions_count,
        total_trainers=total_trainers,
    )
