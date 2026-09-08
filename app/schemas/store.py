import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import OrderStatus, PaymentStatus
from app.schemas.common import IDModel, TimestampedModel


class ProductCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None


class ProductCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    is_active: bool | None = None


class ProductCategoryRead(TimestampedModel):
    name: str
    description: str | None
    is_active: bool


class ProductImageRead(IDModel):
    url: str
    order_index: int


class ProductCreate(BaseModel):
    category_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    price: Decimal = Field(gt=0)
    sku: str = Field(min_length=1, max_length=64)
    stock_quantity: int = Field(ge=0)


class ProductUpdate(BaseModel):
    category_id: uuid.UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0)
    is_active: bool | None = None


class ProductStockAdjust(BaseModel):
    delta: int
    reason: str = Field(min_length=1, max_length=200)


class ProductRead(TimestampedModel):
    category_id: uuid.UUID
    name: str
    description: str | None
    price: Decimal
    sku: str
    stock_quantity: int
    is_active: bool
    images: list[ProductImageRead]
    effective_price: Decimal | None = None


class CartItemAdd(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(gt=0, le=999)


class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0, le=999)


class CartItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    product_id: uuid.UUID
    product: ProductRead
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class CartRead(BaseModel):
    id: uuid.UUID
    items: list[CartItemRead]
    subtotal: Decimal
    discount_total: Decimal
    total: Decimal


class CheckoutRequest(BaseModel):
    delivery_address: str = Field(min_length=1, max_length=1000)
    phone: str = Field(min_length=1, max_length=30)
    notes: str | None = None


class OrderItemRead(IDModel):
    product_id: uuid.UUID
    product_name_snapshot: str
    unit_price: Decimal
    quantity: int
    subtotal: Decimal


class OrderRead(TimestampedModel):
    member_id: uuid.UUID
    status: OrderStatus
    payment_status: PaymentStatus
    subtotal: Decimal
    discount_total: Decimal
    total: Decimal
    delivery_address: str
    phone: str
    notes: str | None
    items: list[OrderItemRead]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderPaymentConfirm(BaseModel):
    notes: str | None = None
