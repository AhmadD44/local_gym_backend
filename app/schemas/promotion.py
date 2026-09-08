import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.enums import DiscountType
from app.schemas.common import TimestampedModel


class PromotionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    discount_type: DiscountType
    discount_value: Decimal = Field(gt=0)
    start_date: datetime
    end_date: datetime
    stack_priority: int = 100
    combinable: bool = False
    product_ids: list[uuid.UUID] = Field(default_factory=list)
    category_ids: list[uuid.UUID] = Field(default_factory=list)
    plan_ids: list[uuid.UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_dates_and_value(self) -> "PromotionCreate":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        if self.discount_type == DiscountType.PERCENTAGE and self.discount_value > 100:
            raise ValueError("percentage discount cannot exceed 100")
        return self


class PromotionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    discount_value: Decimal | None = Field(default=None, gt=0)
    start_date: datetime | None = None
    end_date: datetime | None = None
    is_active: bool | None = None
    stack_priority: int | None = None
    combinable: bool | None = None


class PromotionRead(TimestampedModel):
    name: str
    description: str | None
    discount_type: DiscountType
    discount_value: Decimal
    start_date: datetime
    end_date: datetime
    is_active: bool
    stack_priority: int
    combinable: bool
    product_ids: list[uuid.UUID] = Field(default_factory=list)
    category_ids: list[uuid.UUID] = Field(default_factory=list)
    plan_ids: list[uuid.UUID] = Field(default_factory=list)
