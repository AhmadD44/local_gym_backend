from decimal import Decimal

from app.models.enums import DiscountType
from app.models.promotion import Promotion
from app.services.promotion_service import apply_stacked_discount


def _promo(discount_type, value, combinable=False, stack_priority=100) -> Promotion:
    return Promotion(
        name="test",
        discount_type=discount_type,
        discount_value=Decimal(value),
        combinable=combinable,
        stack_priority=stack_priority,
    )


def test_no_promotions_no_discount():
    assert apply_stacked_discount(Decimal("100"), []) == Decimal("0")


def test_single_percentage_discount():
    promo = _promo(DiscountType.PERCENTAGE, "10")
    assert apply_stacked_discount(Decimal("100"), [promo]) == Decimal("10.00")


def test_single_fixed_discount_capped_at_subtotal():
    promo = _promo(DiscountType.FIXED, "500")
    assert apply_stacked_discount(Decimal("100"), [promo]) == Decimal("100.00")


def test_non_combinable_only_best_applies():
    cheap = _promo(DiscountType.PERCENTAGE, "5")
    best = _promo(DiscountType.PERCENTAGE, "20")
    assert apply_stacked_discount(Decimal("100"), [cheap, best]) == Decimal("20.00")


def test_combinable_promotions_stack():
    a = _promo(DiscountType.PERCENTAGE, "10", combinable=True)
    b = _promo(DiscountType.FIXED, "5", combinable=True)
    # 10% of 100 = 10, then 5 fixed off the remaining 90 => 15 total discount
    assert apply_stacked_discount(Decimal("100"), [a, b]) == Decimal("15.00")


def test_combinable_and_non_combinable_mixed():
    non_combinable = _promo(DiscountType.PERCENTAGE, "10")
    combinable = _promo(DiscountType.FIXED, "5", combinable=True)
    discount = apply_stacked_discount(Decimal("100"), [non_combinable, combinable])
    assert discount == Decimal("15.00")


def test_discount_never_exceeds_base_amount():
    a = _promo(DiscountType.FIXED, "80", combinable=True)
    b = _promo(DiscountType.FIXED, "80", combinable=True)
    assert apply_stacked_discount(Decimal("100"), [a, b]) == Decimal("100.00")
