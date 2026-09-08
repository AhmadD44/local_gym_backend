import uuid

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.pagination import Page, PageParams, paginate
from app.core.permissions import get_member_profile_for_user, require_admin, require_role
from app.models.enums import InventoryReason, OrderStatus, UserRole
from app.models.store import Product, ProductCategory, ProductImage
from app.models.user import User
from app.schemas.store import (
    CartItemAdd,
    CartItemRead,
    CartItemUpdate,
    CartRead,
    CheckoutRequest,
    OrderRead,
    OrderStatusUpdate,
    ProductCategoryCreate,
    ProductCategoryRead,
    ProductCategoryUpdate,
    ProductCreate,
    ProductRead,
    ProductStockAdjust,
    ProductUpdate,
)
from app.services import store_service
from app.services.promotion_service import apply_stacked_discount, get_active_promotions_for_product
from app.utils.uploads import validate_and_store_image

router = APIRouter(prefix="/store", tags=["store"])


# ---- Categories -----------------------------------------------------------


@router.get("/categories", response_model=list[ProductCategoryRead], summary="List product categories")
async def list_categories(db: AsyncSession = Depends(get_db), active_only: bool = True):
    stmt = select(ProductCategory)
    if active_only:
        stmt = stmt.where(ProductCategory.is_active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post(
    "/categories",
    response_model=ProductCategoryRead,
    status_code=201,
    dependencies=[Depends(require_admin)],
    summary="Create a product category (admin only)",
)
async def create_category(payload: ProductCategoryCreate, db: AsyncSession = Depends(get_db)):
    category = ProductCategory(**payload.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.patch(
    "/categories/{category_id}",
    response_model=ProductCategoryRead,
    dependencies=[Depends(require_admin)],
    summary="Update a product category (admin only)",
)
async def update_category(
    category_id: uuid.UUID, payload: ProductCategoryUpdate, db: AsyncSession = Depends(get_db)
):
    category = await db.get(ProductCategory, category_id)
    if category is None:
        raise NotFoundError("Category not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    await db.commit()
    await db.refresh(category)
    return category


# ---- Products ---------------------------------------------------------------


async def _product_to_read(db: AsyncSession, product: Product) -> ProductRead:
    promos = await get_active_promotions_for_product(db, product_id=product.id, category_id=product.category_id)
    discount = apply_stacked_discount(product.price, promos)
    data = ProductRead.model_validate(product)
    data.effective_price = product.price - discount
    return data


@router.get("/products", response_model=Page[ProductRead], summary="List/search products")
async def list_products(
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
    category_id: uuid.UUID | None = None,
    search: str | None = None,
    active_only: bool = True,
):
    stmt = select(Product).options(selectinload(Product.images))
    if active_only:
        stmt = stmt.where(Product.is_active.is_(True))
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if search:
        stmt = stmt.where(Product.name.ilike(f"%{search}%"))
    stmt = stmt.order_by(Product.created_at.desc())

    params = PageParams(page=page, page_size=page_size)
    items, total = await paginate(db, stmt, params)
    read_items = [await _product_to_read(db, p) for p in items]
    return Page.create(read_items, total, params)


@router.get("/products/{product_id}", response_model=ProductRead, summary="Get a product")
async def get_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    product = await store_service.get_product(db, product_id=product_id)
    return await _product_to_read(db, product)


@router.post(
    "/products",
    response_model=ProductRead,
    status_code=201,
    dependencies=[Depends(require_admin)],
    summary="Create a product (admin only)",
)
async def create_product(payload: ProductCreate, db: AsyncSession = Depends(get_db)):
    product = await store_service.create_product(db, data=payload)
    return await _product_to_read(db, product)


@router.patch(
    "/products/{product_id}",
    response_model=ProductRead,
    dependencies=[Depends(require_admin)],
    summary="Update a product (admin only, price/name/category — not stock)",
)
async def update_product(product_id: uuid.UUID, payload: ProductUpdate, db: AsyncSession = Depends(get_db)):
    product = await store_service.update_product(db, product_id=product_id, data=payload)
    return await _product_to_read(db, product)


@router.post(
    "/products/{product_id}/stock",
    response_model=ProductRead,
    dependencies=[Depends(require_admin)],
    summary="Adjust product stock (admin only, auditable inventory movement)",
)
async def adjust_stock(
    product_id: uuid.UUID,
    payload: ProductStockAdjust,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    reason = InventoryReason.RESTOCK if payload.delta > 0 else InventoryReason.ADJUSTMENT
    await store_service.adjust_stock(
        db, product_id=product_id, delta=payload.delta, reason=reason, actor_id=admin.id
    )
    product = await store_service.get_product(db, product_id=product_id)
    return await _product_to_read(db, product)


@router.post(
    "/products/{product_id}/images",
    response_model=ProductRead,
    dependencies=[Depends(require_admin)],
    summary="Upload a product image (admin only)",
)
async def upload_product_image(product_id: uuid.UUID, file: UploadFile, db: AsyncSession = Depends(get_db)):
    product = await store_service.get_product(db, product_id=product_id)
    url = await validate_and_store_image(file, folder="product-images")
    db.add(ProductImage(product_id=product.id, url=url, order_index=len(product.images)))
    await db.commit()
    product = await store_service.get_product(db, product_id=product_id)
    return await _product_to_read(db, product)


# ---- Cart ---------------------------------------------------------------


async def _cart_to_read(db: AsyncSession, cart) -> CartRead:
    subtotal, discount_total, total, lines = await store_service.price_cart(db, cart=cart)
    item_reads: list[CartItemRead] = []
    for item, line in zip(cart.items, lines, strict=False):
        item_reads.append(
            CartItemRead(
                id=item.id,
                product_id=item.product_id,
                product=await _product_to_read(db, line["product"]),
                quantity=item.quantity,
                unit_price=line["unit_price"],
                subtotal=line["line_subtotal"] - line["line_discount"],
            )
        )
    return CartRead(id=cart.id, items=item_reads, subtotal=subtotal, discount_total=discount_total, total=total)


@router.get("/cart", response_model=CartRead, summary="Get my cart")
async def get_cart(db: AsyncSession = Depends(get_db), user: User = Depends(require_role(UserRole.MEMBER))):
    profile = await get_member_profile_for_user(user, db)
    cart = await store_service.get_or_create_cart(db, member_id=profile.id)
    return await _cart_to_read(db, cart)


@router.post("/cart/items", response_model=CartRead, summary="Add a product to my cart")
async def add_cart_item(
    payload: CartItemAdd, db: AsyncSession = Depends(get_db), user: User = Depends(require_role(UserRole.MEMBER))
):
    profile = await get_member_profile_for_user(user, db)
    cart = await store_service.add_to_cart(
        db, member_id=profile.id, product_id=payload.product_id, quantity=payload.quantity
    )
    return await _cart_to_read(db, cart)


@router.patch("/cart/items/{item_id}", response_model=CartRead, summary="Update a cart item's quantity")
async def update_cart_item(
    item_id: uuid.UUID,
    payload: CartItemUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.MEMBER)),
):
    profile = await get_member_profile_for_user(user, db)
    cart = await store_service.update_cart_item(
        db, member_id=profile.id, item_id=item_id, quantity=payload.quantity
    )
    return await _cart_to_read(db, cart)


@router.delete("/cart/items/{item_id}", response_model=CartRead, summary="Remove an item from my cart")
async def remove_cart_item(
    item_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(require_role(UserRole.MEMBER))
):
    profile = await get_member_profile_for_user(user, db)
    cart = await store_service.remove_cart_item(db, member_id=profile.id, item_id=item_id)
    return await _cart_to_read(db, cart)


# ---- Orders / Checkout -----------------------------------------------------


@router.post(
    "/checkout",
    response_model=OrderRead,
    status_code=201,
    summary="Checkout my cart (cash on delivery)",
    description="Prices, discounts and totals are computed entirely server-side from the "
    "current product prices and active promotions — the client only supplies delivery "
    "details. Stock is decremented atomically with row-level locking.",
)
async def checkout(
    payload: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.MEMBER)),
):
    profile = await get_member_profile_for_user(user, db)
    return await store_service.checkout(
        db,
        member_id=profile.id,
        delivery_address=payload.delivery_address,
        phone=payload.phone,
        notes=payload.notes,
    )


@router.get("/orders/me", response_model=list[OrderRead], summary="List my orders")
async def my_orders(db: AsyncSession = Depends(get_db), user: User = Depends(require_role(UserRole.MEMBER))):
    profile = await get_member_profile_for_user(user, db)
    return await store_service.list_member_orders(db, member_id=profile.id)


@router.get("/orders/{order_id}", response_model=OrderRead, summary="Get an order (owner or staff)")
async def get_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.MEMBER, UserRole.ADMIN)),
):
    order = await store_service.get_order_detail(db, order_id=order_id)
    if user.role == UserRole.MEMBER:
        profile = await get_member_profile_for_user(user, db)
        if order.member_id != profile.id:
            raise NotFoundError("Order not found")
    return order


@router.get(
    "/orders",
    response_model=Page[OrderRead],
    dependencies=[Depends(require_admin)],
    summary="List all orders (admin only)",
)
async def list_orders(
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
    status_filter: OrderStatus | None = None,
):
    from app.models.store import StoreOrder

    stmt = select(StoreOrder).options(selectinload(StoreOrder.items)).order_by(StoreOrder.created_at.desc())
    if status_filter:
        stmt = stmt.where(StoreOrder.status == status_filter)
    params = PageParams(page=page, page_size=page_size)
    items, total = await paginate(db, stmt, params)
    return Page.create(items, total, params)


@router.post(
    "/orders/{order_id}/status",
    response_model=OrderRead,
    dependencies=[Depends(require_admin)],
    summary="Transition an order's status (admin only, validated state machine)",
)
async def update_order_status(
    order_id: uuid.UUID,
    payload: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return await store_service.update_order_status(
        db, order_id=order_id, new_status=payload.status, actor_id=admin.id
    )


@router.post(
    "/orders/{order_id}/confirm-payment",
    response_model=OrderRead,
    dependencies=[Depends(require_admin)],
    summary="Confirm cash-on-delivery payment was collected (admin only)",
)
async def confirm_order_payment(
    order_id: uuid.UUID, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)
):
    return await store_service.confirm_order_payment(db, order_id=order_id, actor_id=admin.id)
