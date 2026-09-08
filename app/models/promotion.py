import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import DiscountType


class Promotion(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "promotions"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    discount_type: Mapped[DiscountType] = mapped_column(
        Enum(DiscountType, name="discount_type", native_enum=True), nullable=False
    )
    discount_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    # Lower value = applied first / takes precedence when stacking is not allowed.
    stack_priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    combinable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    products: Mapped[list["PromotionProduct"]] = relationship(
        "PromotionProduct", back_populates="promotion", cascade="all, delete-orphan"
    )
    categories: Mapped[list["PromotionCategory"]] = relationship(
        "PromotionCategory", back_populates="promotion", cascade="all, delete-orphan"
    )
    plans: Mapped[list["PromotionMembershipPlan"]] = relationship(
        "PromotionMembershipPlan", back_populates="promotion", cascade="all, delete-orphan"
    )


class PromotionProduct(Base, UUIDPKMixin):
    __tablename__ = "promotion_products"

    promotion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("promotions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )

    promotion = relationship("Promotion", back_populates="products")


class PromotionCategory(Base, UUIDPKMixin):
    __tablename__ = "promotion_categories"

    promotion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("promotions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_categories.id", ondelete="CASCADE"), nullable=False, index=True
    )

    promotion = relationship("Promotion", back_populates="categories")


class PromotionMembershipPlan(Base, UUIDPKMixin):
    __tablename__ = "promotion_membership_plans"

    promotion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("promotions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("membership_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )

    promotion = relationship("Promotion", back_populates="plans")
