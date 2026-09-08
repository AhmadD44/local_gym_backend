import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.enums import MembershipStatus, PaymentStatus
from app.models.membership import MembershipPlan, MembershipSubscription
from app.services.audit_service import record_audit_log


async def get_active_or_pending_subscription(
    session: AsyncSession, *, member_id: uuid.UUID
) -> MembershipSubscription | None:
    stmt = (
        select(MembershipSubscription)
        .where(
            MembershipSubscription.member_id == member_id,
            MembershipSubscription.status.in_([MembershipStatus.PENDING, MembershipStatus.ACTIVE]),
        )
        .order_by(MembershipSubscription.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().first()


async def subscribe_member(
    session: AsyncSession, *, member_id: uuid.UUID, plan_id: uuid.UUID
) -> MembershipSubscription:
    existing = await get_active_or_pending_subscription(session, member_id=member_id)
    if existing is not None:
        raise ConflictError("Member already has a pending or active membership")

    plan = await session.get(MembershipPlan, plan_id)
    if plan is None or not plan.is_active:
        raise NotFoundError("Membership plan not found")

    subscription = MembershipSubscription(
        member_id=member_id,
        plan_id=plan_id,
        status=MembershipStatus.PENDING,
        payment_status=PaymentStatus.PENDING,
        price_at_purchase=plan.price,
    )
    session.add(subscription)
    try:
        await session.commit()
    except IntegrityError as exc:
        # A concurrent request beat us to it; the partial unique index on
        # (member_id) WHERE status IN ('PENDING','ACTIVE') is the real
        # guarantee here, this is just turning that into a clean 409.
        await session.rollback()
        raise ConflictError("Member already has a pending or active membership") from exc
    await session.refresh(subscription)
    return subscription


async def confirm_payment(
    session: AsyncSession, *, subscription_id: uuid.UUID, admin_id: uuid.UUID, notes: str | None
) -> MembershipSubscription:
    """Only an authorized admin may call this. Cash payment is confirmed
    in person at the gym; there is no online payment path."""
    subscription = await session.get(MembershipSubscription, subscription_id)
    if subscription is None:
        raise NotFoundError("Subscription not found")
    if subscription.payment_status == PaymentStatus.PAID:
        raise ConflictError("Payment already confirmed")
    if subscription.status not in (MembershipStatus.PENDING,):
        raise BadRequestError("Only pending subscriptions can be confirmed")

    plan = await session.get(MembershipPlan, subscription.plan_id)
    if plan is None:
        # Cannot actually happen (plan_id is a NOT NULL FK with ON DELETE
        # RESTRICT), but keep the type checker honest and fail loudly
        # rather than raising AttributeError below if data is ever corrupt.
        raise NotFoundError("Membership plan not found")
    today = date.today()

    # Renewal stacking: if the member has a still-active subscription for
    # the same plan family expiring later, extend from that date instead
    # of from today.
    start = today
    subscription.start_date = start
    subscription.expiry_date = start + timedelta(days=plan.duration_days)
    subscription.status = MembershipStatus.ACTIVE
    subscription.payment_status = PaymentStatus.PAID
    subscription.confirmed_by = admin_id
    subscription.confirmed_at = datetime.now(UTC)
    subscription.notes = notes

    await record_audit_log(
        session,
        actor_id=admin_id,
        action="membership.confirm_payment",
        entity_type="MembershipSubscription",
        entity_id=str(subscription.id),
        after={"status": subscription.status.value, "payment_status": subscription.payment_status.value},
    )
    await session.commit()
    await session.refresh(subscription)
    return subscription


async def extend_subscription(
    session: AsyncSession, *, subscription_id: uuid.UUID, additional_days: int, admin_id: uuid.UUID
) -> MembershipSubscription:
    subscription = await session.get(MembershipSubscription, subscription_id)
    if subscription is None:
        raise NotFoundError("Subscription not found")
    if subscription.status != MembershipStatus.ACTIVE or subscription.expiry_date is None:
        raise BadRequestError("Only active subscriptions can be extended")

    before_expiry = subscription.expiry_date
    subscription.expiry_date = subscription.expiry_date + timedelta(days=additional_days)
    await record_audit_log(
        session,
        actor_id=admin_id,
        action="membership.extend",
        entity_type="MembershipSubscription",
        entity_id=str(subscription.id),
        before={"expiry_date": before_expiry.isoformat()},
        after={"expiry_date": subscription.expiry_date.isoformat()},
    )
    await session.commit()
    await session.refresh(subscription)
    return subscription


async def cancel_subscription(
    session: AsyncSession, *, subscription_id: uuid.UUID, actor_id: uuid.UUID, is_admin: bool
) -> MembershipSubscription:
    subscription = await session.get(MembershipSubscription, subscription_id)
    if subscription is None:
        raise NotFoundError("Subscription not found")
    if subscription.status in (MembershipStatus.CANCELLED, MembershipStatus.EXPIRED):
        raise ConflictError("Subscription already cancelled or expired")
    if not is_admin and subscription.payment_status == PaymentStatus.PAID:
        raise BadRequestError("A paid membership can only be cancelled by an administrator")

    subscription.status = MembershipStatus.CANCELLED
    subscription.cancelled_at = datetime.now(UTC)
    if subscription.payment_status == PaymentStatus.PAID:
        subscription.payment_status = PaymentStatus.REFUNDED if is_admin else subscription.payment_status

    await record_audit_log(
        session,
        actor_id=actor_id,
        action="membership.cancel",
        entity_type="MembershipSubscription",
        entity_id=str(subscription.id),
    )
    await session.commit()
    await session.refresh(subscription)
    return subscription


async def expire_stale_subscriptions(session: AsyncSession) -> int:
    """Marks ACTIVE subscriptions past their expiry date as EXPIRED.
    Intended to be invoked by a periodic scheduled job."""
    today = date.today()
    stmt = select(MembershipSubscription).where(
        MembershipSubscription.status == MembershipStatus.ACTIVE,
        MembershipSubscription.expiry_date < today,
    )
    result = await session.execute(stmt)
    stale = list(result.scalars().all())
    for sub in stale:
        sub.status = MembershipStatus.EXPIRED
    if stale:
        await session.commit()
    return len(stale)
