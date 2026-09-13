import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.api.v1.endpoints import memberships
from app.models.enums import DiscountType
from app.models.membership import MembershipPlan
from app.models.promotion import Promotion, PromotionCategory, PromotionProduct
from app.schemas.promotion import PromotionUpdate
from app.services import membership_service, promotion_service


def offer(value="20", discount_type=DiscountType.PERCENTAGE):
    return Promotion(
        name="Member offer", discount_type=discount_type,
        discount_value=Decimal(value), combinable=False, stack_priority=100,
    )


def plan():
    now = datetime.now(UTC)
    return MembershipPlan(
        id=uuid.uuid4(), name="Monthly", description=None, duration_days=30,
        price=Decimal("100"), is_active=True, created_at=now, updated_at=now,
    )


@pytest.mark.parametrize("promotions,expected", [
    ([offer()], "80.00"), ([], "100"), ([offer("500", DiscountType.FIXED)], "0.00"),
])
async def test_subscription_snapshots_server_discount(monkeypatch, promotions, expected):
    member_id = uuid.uuid4()
    membership_plan = plan()
    db = SimpleNamespace(get=AsyncMock(return_value=membership_plan), add=Mock(),
                         commit=AsyncMock(), refresh=AsyncMock())
    monkeypatch.setattr(membership_service, "get_active_or_pending_subscription", AsyncMock(return_value=None))
    eligible = AsyncMock(return_value=promotions)
    monkeypatch.setattr(membership_service, "get_active_promotions_for_plan", eligible)
    subscription = await membership_service.subscribe_member(db, member_id=member_id, plan_id=membership_plan.id)
    assert subscription.price_at_purchase == Decimal(expected)
    assert membership_plan.price == Decimal("100")
    eligible.assert_awaited_once_with(db, plan_id=membership_plan.id)
    db.add.assert_called_once_with(subscription)
    db.commit.assert_awaited_once()


async def test_plan_listing_exposes_discounted_price_without_changing_base_price(monkeypatch):
    membership_plan = plan()
    result = Mock()
    result.scalars.return_value.all.return_value = [membership_plan]
    db = SimpleNamespace(execute=AsyncMock(return_value=result))
    monkeypatch.setattr(memberships, "get_active_promotions_for_plan", AsyncMock(return_value=[offer()]))
    items = await memberships.list_plans(db=db)
    assert items[0].price == Decimal("100")
    assert items[0].effective_price == Decimal("80.00")


async def test_edit_promotion_replaces_requested_targets_and_preserves_omitted_links(monkeypatch):
    product_id, old_category_id, new_category_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    promotion = offer()
    promotion.id = uuid.uuid4()
    promotion.products = [PromotionProduct(product_id=product_id)]
    promotion.categories = [PromotionCategory(category_id=old_category_id)]
    promotion.plans = []
    monkeypatch.setattr(promotion_service, "get_promotion", AsyncMock(return_value=promotion))
    db = SimpleNamespace(commit=AsyncMock())
    updated = await promotion_service.update_promotion(db, promotion_id=promotion.id,
        data=PromotionUpdate(category_ids=[new_category_id, new_category_id]))
    assert [p.product_id for p in updated.products] == [product_id]
    assert [c.category_id for c in updated.categories] == [new_category_id]
    await promotion_service.update_promotion(db, promotion_id=promotion.id, data=PromotionUpdate(category_ids=[]))
    assert promotion.categories == []
    assert [p.product_id for p in promotion.products] == [product_id]
