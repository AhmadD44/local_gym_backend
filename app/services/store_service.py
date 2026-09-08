"""Store domain: products, cart, checkout, inventory.

Concurrency safety:
- `adjust_stock` and checkout both take a row-level lock
  (`SELECT ... FOR UPDATE`) on the affected Product row(s) before reading
  `stock_quantity`, so two simultaneous purchases of the last unit cannot
  both succeed (mirrors the class-capacity protection).
- When checkout touches multiple products, rows are locked in a
  deterministic order (sorted by product id) to avoid deadlocks between
  two concurrent checkouts that share products.
- `stock_quantity` also carries a DB CHECK constraint (>= 0) as a second
  line of defense.

Pricing safety: the client only ever sends `product_id` + `quantity`.
Unit price, discounts, and totals are always computed here from the
current Product row and active Promotion rows — never trusted from the
request body.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.enums import InventoryReason, OrderStatus, PaymentStatus
from app.models.store import CartItem, InventoryMovement, Product, ShoppingCart, StoreOrder, StoreOrderItem
from app.services.audit_service import record_audit_log
from app.services.promotion_service import apply_stacked_discount, get_active_promotions_for_product

ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.OUT_FOR_DELIVERY},
    OrderStatus.OUT_FOR_DELIVERY: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}
CANCELLABLE_STATUSES = {OrderStatus.PENDING, OrderStatus.CONFIRMED}


async def adjust_stock(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    delta: int,
    reason: InventoryReason,
    actor_id: uuid.UUID | None,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
) -> Product:
    result = await session.execute(select(Product).where(Product.id == product_id).with_for_update())
    product = result.scalar_one_or_none()
    if product is None:
        raise NotFoundError("Product not found")

    new_quantity = product.stock_quantity + delta
    if new_quantity < 0:
        raise ConflictError("Insufficient stock")

    product.stock_quantity = new_quantity
    session.add(
        InventoryMovement(
            product_id=product_id,
            change_qty=delta,
            reason=reason,
            reference_type=reference_type,
            reference_id=reference_id,
            created_at=datetime.now(UTC),
            created_by=actor_id,
        )
    )
    await session.commit()
    await session.refresh(product)
    return product


async def create_product(session: AsyncSession, *, data) -> Product:
    existing = await session.execute(select(Product.id).where(Product.sku == data.sku))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("A product with this SKU already exists")
    product = Product(**data.model_dump())
    session.add(product)
    await session.commit()
    # session.refresh() only reloads column attributes, not the `images`
    # relationship — ProductRead.model_validate() (called by every caller
    # of create_product/update_product) reads product.images, and an
    # unloaded relationship accessed outside an awaited context raises
    # MissingGreenlet. get_product() already eager-loads it correctly, so
    # reuse it instead of duplicating the eager-load option here.
    return await get_product(session, product_id=product.id)


async def update_product(session: AsyncSession, *, product_id: uuid.UUID, data) -> Product:
    product = await session.get(Product, product_id)
    if product is None:
        raise NotFoundError("Product not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    await session.commit()
    return await get_product(session, product_id=product_id)


async def get_product(session: AsyncSession, *, product_id: uuid.UUID) -> Product:
    result = await session.execute(
        select(Product).where(Product.id == product_id).options(selectinload(Product.images))
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise NotFoundError("Product not found")
    return product


async def get_or_create_cart(session: AsyncSession, *, member_id: uuid.UUID) -> ShoppingCart:
    result = await session.execute(
        select(ShoppingCart).where(ShoppingCart.member_id == member_id).options(selectinload(ShoppingCart.items))
    )
    cart = result.scalar_one_or_none()
    if cart is None:
        cart = ShoppingCart(member_id=member_id)
        session.add(cart)
        await session.commit()
        # session.refresh() only reloads column attributes, not
        # relationships, so `cart.items` would stay unloaded here and any
        # later synchronous access (e.g. `for i in cart.items`) would try
        # an implicit lazy-load outside of an awaited context and raise
        # MissingGreenlet. Re-fetch with the same eager-load option instead.
        result = await session.execute(
            select(ShoppingCart).where(ShoppingCart.id == cart.id).options(selectinload(ShoppingCart.items))
        )
        cart = result.scalar_one()
    return cart


async def add_to_cart(
    session: AsyncSession, *, member_id: uuid.UUID, product_id: uuid.UUID, quantity: int
) -> ShoppingCart:
    product = await session.get(Product, product_id)
    if product is None or not product.is_active:
        raise NotFoundError("Product not found")

    cart = await get_or_create_cart(session, member_id=member_id)
    existing = next((i for i in cart.items if i.product_id == product_id), None)
    if existing is not None:
        existing.quantity += quantity
    else:
        cart.items.append(CartItem(cart_id=cart.id, product_id=product_id, quantity=quantity))
    await session.commit()
    return await get_or_create_cart(session, member_id=member_id)


async def update_cart_item(
    session: AsyncSession, *, member_id: uuid.UUID, item_id: uuid.UUID, quantity: int
) -> ShoppingCart:
    cart = await get_or_create_cart(session, member_id=member_id)
    item = next((i for i in cart.items if i.id == item_id), None)
    if item is None:
        raise NotFoundError("Cart item not found")
    item.quantity = quantity
    await session.commit()
    return await get_or_create_cart(session, member_id=member_id)


async def remove_cart_item(session: AsyncSession, *, member_id: uuid.UUID, item_id: uuid.UUID) -> ShoppingCart:
    cart = await get_or_create_cart(session, member_id=member_id)
    item = next((i for i in cart.items if i.id == item_id), None)
    if item is None:
        raise NotFoundError("Cart item not found")
    await session.delete(item)
    await session.commit()
    return await get_or_create_cart(session, member_id=member_id)


async def price_cart(session: AsyncSession, *, cart: ShoppingCart) -> tuple[Decimal, Decimal, Decimal, list[dict]]:
    """Returns (subtotal, discount_total, total, priced_lines) computed
    entirely server-side."""
    subtotal = Decimal("0")
    discount_total = Decimal("0")
    lines = []
    for item in cart.items:
        # `options=` eager-loads `images` so the later ProductRead.model_
        # validate() (which reads product.images) doesn't trigger an
        # implicit lazy-load outside an awaited context (MissingGreenlet).
        product = await session.get(Product, item.product_id, options=[selectinload(Product.images)])
        if product is None:
            continue
        line_subtotal = product.price * item.quantity
        promos = await get_active_promotions_for_product(
            session, product_id=product.id, category_id=product.category_id
        )
        line_discount = apply_stacked_discount(line_subtotal, promos)
        subtotal += line_subtotal
        discount_total += line_discount
        lines.append(
            {
                "product": product,
                "quantity": item.quantity,
                "unit_price": product.price,
                "line_subtotal": line_subtotal,
                "line_discount": line_discount,
            }
        )
    total = subtotal - discount_total
    return subtotal, discount_total, total, lines


async def checkout(
    session: AsyncSession, *, member_id: uuid.UUID, delivery_address: str, phone: str, notes: str | None
) -> StoreOrder:
    cart = await get_or_create_cart(session, member_id=member_id)
    if not cart.items:
        raise BadRequestError("Cart is empty")

    # Lock product rows in a deterministic order to avoid deadlocks between
    # concurrent checkouts that share products.
    product_ids = sorted({item.product_id for item in cart.items}, key=str)
    locked_products: dict[uuid.UUID, Product] = {}
    for pid in product_ids:
        result = await session.execute(select(Product).where(Product.id == pid).with_for_update())
        product = result.scalar_one_or_none()
        if product is None or not product.is_active:
            raise BadRequestError("One or more products in your cart are no longer available")
        locked_products[pid] = product

    for item in cart.items:
        product = locked_products[item.product_id]
        if product.stock_quantity < item.quantity:
            raise ConflictError(f"Insufficient stock for {product.name}")

    subtotal = Decimal("0")
    discount_total = Decimal("0")
    order_items: list[StoreOrderItem] = []
    for item in cart.items:
        product = locked_products[item.product_id]
        line_subtotal = product.price * item.quantity
        promos = await get_active_promotions_for_product(
            session, product_id=product.id, category_id=product.category_id
        )
        line_discount = apply_stacked_discount(line_subtotal, promos)
        subtotal += line_subtotal
        discount_total += line_discount
        order_items.append(
            StoreOrderItem(
                product_id=product.id,
                product_name_snapshot=product.name,
                unit_price=product.price,
                quantity=item.quantity,
                subtotal=line_subtotal - line_discount,
            )
        )

    total = subtotal - discount_total
    order = StoreOrder(
        member_id=member_id,
        status=OrderStatus.PENDING,
        payment_status=PaymentStatus.PENDING,
        subtotal=subtotal,
        discount_total=discount_total,
        total=total,
        delivery_address=delivery_address,
        phone=phone,
        notes=notes,
    )
    order.items = order_items
    session.add(order)
    await session.flush()

    for item in cart.items:
        product = locked_products[item.product_id]
        product.stock_quantity -= item.quantity
        session.add(
            InventoryMovement(
                product_id=product.id,
                change_qty=-item.quantity,
                reason=InventoryReason.SALE,
                reference_type="StoreOrder",
                reference_id=order.id,
                created_at=datetime.now(UTC),
                created_by=None,
            )
        )
        await session.delete(item)

    await session.commit()
    return await get_order_detail(session, order_id=order.id)


async def get_order_detail(session: AsyncSession, *, order_id: uuid.UUID) -> StoreOrder:
    result = await session.execute(
        select(StoreOrder).where(StoreOrder.id == order_id).options(selectinload(StoreOrder.items))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise NotFoundError("Order not found")
    return order


async def update_order_status(
    session: AsyncSession, *, order_id: uuid.UUID, new_status: OrderStatus, actor_id: uuid.UUID
) -> StoreOrder:
    order = await get_order_detail(session, order_id=order_id)
    allowed = ORDER_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise BadRequestError(f"Cannot transition order from {order.status.value} to {new_status.value}")

    if new_status == OrderStatus.CANCELLED:
        if order.status not in CANCELLABLE_STATUSES:
            raise BadRequestError("Order can no longer be cancelled")
        for item in order.items:
            await adjust_stock(
                session,
                product_id=item.product_id,
                delta=item.quantity,
                reason=InventoryReason.ORDER_CANCELLED,
                actor_id=actor_id,
                reference_type="StoreOrder",
                reference_id=order.id,
            )

    before = {"status": order.status.value}
    order.status = new_status
    await record_audit_log(
        session,
        actor_id=actor_id,
        action="order.status_change",
        entity_type="StoreOrder",
        entity_id=str(order.id),
        before=before,
        after={"status": new_status.value},
    )
    await session.commit()
    return await get_order_detail(session, order_id=order_id)


async def confirm_order_payment(session: AsyncSession, *, order_id: uuid.UUID, actor_id: uuid.UUID) -> StoreOrder:
    order = await get_order_detail(session, order_id=order_id)
    if order.status not in (OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED):
        raise BadRequestError("Payment can only be confirmed once the order is out for delivery or delivered")
    if order.payment_status == PaymentStatus.PAID:
        raise ConflictError("Payment already confirmed")

    order.payment_status = PaymentStatus.PAID
    order.confirmed_by = actor_id
    await record_audit_log(
        session,
        actor_id=actor_id,
        action="order.confirm_payment",
        entity_type="StoreOrder",
        entity_id=str(order.id),
    )
    await session.commit()
    return await get_order_detail(session, order_id=order_id)


async def list_member_orders(session: AsyncSession, *, member_id: uuid.UUID) -> list[StoreOrder]:
    result = await session.execute(
        select(StoreOrder)
        .where(StoreOrder.member_id == member_id)
        .options(selectinload(StoreOrder.items))
        .order_by(StoreOrder.created_at.desc())
    )
    return list(result.scalars().unique().all())
