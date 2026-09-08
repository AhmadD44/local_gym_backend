"""Server-side discount calculation. The client never sends discount or
total amounts — every price is loaded from PostgreSQL and every discount
is computed here from active Promotion rows.

Stacking rule (documented and enforced, not left ambiguous):
- Promotions marked `combinable=True` always stack together (their
  discounts are summed).
- Among `combinable=False` promotions applicable to the same line, only
  the single one that yields the largest discount for the customer is
  applied (ties broken by the lowest `stack_priority` value).
- The final discount for a line can never exceed that line's subtotal
  (no negative totals).
- Expired, not-yet-started, or `is_active=False` promotions are never
  considered, regardless of what a client requests.
"""

import uuid
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.promotion import Promotion, PromotionCategory, PromotionMembershipPlan, PromotionProduct

TWO_PLACES = Decimal("0.01")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


async def get_active_promotions_for_product(
    session: AsyncSession, *, product_id: uuid.UUID, category_id: uuid.UUID
) -> list[Promotion]:
    now = datetime.now(UTC)
    stmt = (
        select(Promotion)
        .distinct()
        .outerjoin(PromotionProduct, PromotionProduct.promotion_id == Promotion.id)
        .outerjoin(PromotionCategory, PromotionCategory.promotion_id == Promotion.id)
        .where(
            Promotion.is_active.is_(True),
            Promotion.start_date <= now,
            Promotion.end_date >= now,
            (PromotionProduct.product_id == product_id) | (PromotionCategory.category_id == category_id),
        )
    )
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def get_active_promotions_for_plan(session: AsyncSession, *, plan_id: uuid.UUID) -> list[Promotion]:
    now = datetime.now(UTC)
    stmt = (
        select(Promotion)
        .join(PromotionMembershipPlan, PromotionMembershipPlan.promotion_id == Promotion.id)
        .where(
            Promotion.is_active.is_(True),
            Promotion.start_date <= now,
            Promotion.end_date >= now,
            PromotionMembershipPlan.plan_id == plan_id,
        )
    )
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


def _discount_amount(promotion: Promotion, base_amount: Decimal) -> Decimal:
    if base_amount <= 0:
        return Decimal("0")
    if promotion.discount_type.value == "PERCENTAGE":
        amount = base_amount * (promotion.discount_value / Decimal("100"))
    else:
        amount = promotion.discount_value
    return min(amount, base_amount)


def apply_stacked_discount(base_amount: Decimal, promotions: list[Promotion]) -> Decimal:
    if not promotions or base_amount <= 0:
        return Decimal("0")

    non_combinable = [p for p in promotions if not p.combinable]
    combinable = [p for p in promotions if p.combinable]

    discount = Decimal("0")
    if non_combinable:
        best = max(
            non_combinable,
            key=lambda p: (_discount_amount(p, base_amount), -p.stack_priority),
        )
        discount += _discount_amount(best, base_amount)

    for promo in combinable:
        discount += _discount_amount(promo, base_amount - discount if base_amount - discount > 0 else Decimal("0"))

    return _quantize(min(discount, base_amount))


async def create_promotion(session: AsyncSession, *, data) -> Promotion:
    promotion = Promotion(
        name=data.name,
        description=data.description,
        discount_type=data.discount_type,
        discount_value=data.discount_value,
        start_date=data.start_date,
        end_date=data.end_date,
        stack_priority=data.stack_priority,
        combinable=data.combinable,
    )
    for pid in data.product_ids:
        promotion.products.append(PromotionProduct(product_id=pid))
    for cid in data.category_ids:
        promotion.categories.append(PromotionCategory(category_id=cid))
    for plid in data.plan_ids:
        promotion.plans.append(PromotionMembershipPlan(plan_id=plid))
    session.add(promotion)
    await session.commit()
    return await get_promotion(session, promotion_id=promotion.id)


async def get_promotion(session: AsyncSession, *, promotion_id: uuid.UUID) -> Promotion:
    from app.core.exceptions import NotFoundError

    result = await session.execute(
        select(Promotion)
        .where(Promotion.id == promotion_id)
        .options(
            selectinload(Promotion.products), selectinload(Promotion.categories), selectinload(Promotion.plans)
        )
    )
    promotion = result.scalar_one_or_none()
    if promotion is None:
        raise NotFoundError("Promotion not found")
    return promotion


async def update_promotion(session: AsyncSession, *, promotion_id: uuid.UUID, data) -> Promotion:
    promotion = await get_promotion(session, promotion_id=promotion_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(promotion, field, value)
    await session.commit()
    return await get_promotion(session, promotion_id=promotion_id)


async def list_all_promotions(session: AsyncSession) -> list[Promotion]:
    result = await session.execute(
        select(Promotion).options(
            selectinload(Promotion.products), selectinload(Promotion.categories), selectinload(Promotion.plans)
        )
    )
    return list(result.scalars().unique().all())


def promotion_to_read(promotion: Promotion):
    from app.schemas.promotion import PromotionRead

    return PromotionRead(
        id=promotion.id,
        created_at=promotion.created_at,
        updated_at=promotion.updated_at,
        name=promotion.name,
        description=promotion.description,
        discount_type=promotion.discount_type,
        discount_value=promotion.discount_value,
        start_date=promotion.start_date,
        end_date=promotion.end_date,
        is_active=promotion.is_active,
        stack_priority=promotion.stack_priority,
        combinable=promotion.combinable,
        product_ids=[p.product_id for p in promotion.products],
        category_ids=[c.category_id for c in promotion.categories],
        plan_ids=[p.plan_id for p in promotion.plans],
    )


async def list_active_promotions(session: AsyncSession) -> list[Promotion]:
    now = datetime.now(UTC)
    stmt = (
        select(Promotion)
        .where(Promotion.is_active.is_(True), Promotion.start_date <= now, Promotion.end_date >= now)
        .options(
            selectinload(Promotion.products), selectinload(Promotion.categories), selectinload(Promotion.plans)
        )
    )
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())
