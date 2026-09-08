import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.permissions import get_member_profile_for_user, require_admin, require_role
from app.models.enums import UserRole
from app.models.membership import MembershipPlan, MembershipSubscription
from app.models.user import User
from app.schemas.membership import (
    MembershipConfirmPaymentRequest,
    MembershipExtendRequest,
    MembershipPlanCreate,
    MembershipPlanRead,
    MembershipPlanUpdate,
    MembershipSubscribeRequest,
    MembershipSubscriptionRead,
)
from app.services import membership_service

router = APIRouter(prefix="/memberships", tags=["memberships"])


@router.get("/plans", response_model=list[MembershipPlanRead], summary="List membership plans")
async def list_plans(db: AsyncSession = Depends(get_db), active_only: bool = True):
    stmt = select(MembershipPlan)
    if active_only:
        stmt = stmt.where(MembershipPlan.is_active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post(
    "/plans",
    response_model=MembershipPlanRead,
    status_code=201,
    dependencies=[Depends(require_admin)],
    summary="Create a membership plan (admin only)",
)
async def create_plan(payload: MembershipPlanCreate, db: AsyncSession = Depends(get_db)):
    plan = MembershipPlan(**payload.model_dump())
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.patch(
    "/plans/{plan_id}",
    response_model=MembershipPlanRead,
    dependencies=[Depends(require_admin)],
    summary="Update a membership plan (admin only)",
)
async def update_plan(plan_id: uuid.UUID, payload: MembershipPlanUpdate, db: AsyncSession = Depends(get_db)):
    plan = await db.get(MembershipPlan, plan_id)
    if plan is None:
        raise NotFoundError("Plan not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.get(
    "/me",
    response_model=MembershipSubscriptionRead | None,
    summary="Get my current/latest membership subscription",
)
async def get_my_membership(
    db: AsyncSession = Depends(get_db), user: User = Depends(require_role(UserRole.MEMBER))
):
    profile = await get_member_profile_for_user(user, db)
    result = await db.execute(
        select(MembershipSubscription)
        .where(MembershipSubscription.member_id == profile.id)
        .options(selectinload(MembershipSubscription.plan))
        .order_by(MembershipSubscription.created_at.desc())
        .limit(1)
    )
    return result.scalars().first()


@router.post(
    "/subscribe",
    response_model=MembershipSubscriptionRead,
    status_code=201,
    summary="Subscribe to a plan (creates a PENDING subscription; payment confirmed in person)",
)
async def subscribe(
    payload: MembershipSubscribeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.MEMBER)),
):
    profile = await get_member_profile_for_user(user, db)
    subscription = await membership_service.subscribe_member(db, member_id=profile.id, plan_id=payload.plan_id)
    result = await db.execute(
        select(MembershipSubscription)
        .where(MembershipSubscription.id == subscription.id)
        .options(selectinload(MembershipSubscription.plan))
    )
    return result.scalar_one()


@router.post(
    "/{subscription_id}/confirm-payment",
    response_model=MembershipSubscriptionRead,
    dependencies=[Depends(require_admin)],
    summary="Confirm cash payment and activate membership (admin only)",
    description="Members can never activate their own membership; only an authorized admin "
    "confirming cash received at the gym can transition a subscription to ACTIVE/PAID.",
)
async def confirm_payment(
    subscription_id: uuid.UUID,
    payload: MembershipConfirmPaymentRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    subscription = await membership_service.confirm_payment(
        db, subscription_id=subscription_id, admin_id=admin.id, notes=payload.notes
    )
    result = await db.execute(
        select(MembershipSubscription)
        .where(MembershipSubscription.id == subscription.id)
        .options(selectinload(MembershipSubscription.plan))
    )
    return result.scalar_one()


@router.post(
    "/{subscription_id}/extend",
    response_model=MembershipSubscriptionRead,
    dependencies=[Depends(require_admin)],
    summary="Extend an active membership by N days (admin only)",
)
async def extend(
    subscription_id: uuid.UUID,
    payload: MembershipExtendRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    subscription = await membership_service.extend_subscription(
        db, subscription_id=subscription_id, additional_days=payload.additional_days, admin_id=admin.id
    )
    result = await db.execute(
        select(MembershipSubscription)
        .where(MembershipSubscription.id == subscription.id)
        .options(selectinload(MembershipSubscription.plan))
    )
    return result.scalar_one()


@router.post(
    "/{subscription_id}/cancel",
    response_model=MembershipSubscriptionRead,
    summary="Cancel a membership subscription",
    description="Members may cancel their own unpaid (PENDING) subscription; cancelling a "
    "PAID subscription requires an admin.",
)
async def cancel(
    subscription_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.MEMBER, UserRole.ADMIN)),
):
    subscription = await db.get(MembershipSubscription, subscription_id)
    if subscription is None:
        raise NotFoundError("Subscription not found")
    if user.role == UserRole.MEMBER:
        profile = await get_member_profile_for_user(user, db)
        if subscription.member_id != profile.id:
            raise NotFoundError("Subscription not found")

    result = await membership_service.cancel_subscription(
        db, subscription_id=subscription_id, actor_id=user.id, is_admin=user.role == UserRole.ADMIN
    )
    full = await db.execute(
        select(MembershipSubscription)
        .where(MembershipSubscription.id == result.id)
        .options(selectinload(MembershipSubscription.plan))
    )
    return full.scalar_one()
