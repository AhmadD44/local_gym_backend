import asyncio

from app.models.store import Product, ProductCategory


async def _make_product(db_session, *, stock=10, price="20.00"):
    category = ProductCategory(name="Supplements")
    db_session.add(category)
    await db_session.flush()
    product = Product(
        category_id=category.id,
        name="Protein Powder",
        price=price,
        sku=f"SKU-{id(category)}",
        stock_quantity=stock,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


async def test_admin_can_create_and_update_product_via_api(client, admin_user, auth_headers):
    """Regression test: create_product/update_product previously crashed
    with a 500 (MissingGreenlet) because the newly created/updated Product
    wasn't eager-loaded before being serialized through ProductRead (which
    reads `images`) — the product was actually saved to the DB despite the
    500, which is worse than an outright failure. This exercises the admin
    HTTP endpoints directly, unlike other tests here which create products
    straight through the DB session."""
    admin, _ = admin_user
    headers = await auth_headers(admin)

    category = await client.post("/api/v1/store/categories", json={"name": "Supplements"}, headers=headers)
    assert category.status_code == 201
    category_id = category.json()["id"]

    created = await client.post(
        "/api/v1/store/products",
        json={
            "category_id": category_id,
            "name": "Protein",
            "price": "29.99",
            "sku": "PROT-API-1",
            "stock_quantity": 10,
        },
        headers=headers,
    )
    assert created.status_code == 201
    body = created.json()
    assert body["price"] == "29.99"
    assert body["images"] == []
    product_id = body["id"]

    updated = await client.patch(f"/api/v1/store/products/{product_id}", json={"price": "34.99"}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["price"] == "34.99"


async def test_checkout_computes_price_server_side_ignoring_client_totals(
    client, db_session, member_user, auth_headers
):
    product = await _make_product(db_session, stock=10, price="25.00")
    user, _ = member_user
    headers = await auth_headers(user)

    add = await client.post(
        "/api/v1/store/cart/items", json={"product_id": str(product.id), "quantity": 2}, headers=headers
    )
    assert add.status_code == 200
    cart = add.json()
    assert cart["total"] == "50.00"  # server-computed, not client supplied

    checkout = await client.post(
        "/api/v1/store/checkout",
        json={"delivery_address": "123 Main St", "phone": "555-0000"},
        headers=headers,
    )
    assert checkout.status_code == 201
    order = checkout.json()
    assert order["total"] == "50.00"
    assert order["status"] == "PENDING"
    assert order["payment_status"] == "PENDING"


async def test_checkout_fails_when_insufficient_stock(client, db_session, member_user, auth_headers):
    product = await _make_product(db_session, stock=1)
    user, _ = member_user
    headers = await auth_headers(user)

    await client.post(
        "/api/v1/store/cart/items", json={"product_id": str(product.id), "quantity": 5}, headers=headers
    )
    checkout = await client.post(
        "/api/v1/store/checkout", json={"delivery_address": "addr", "phone": "555"}, headers=headers
    )
    assert checkout.status_code == 409


async def test_concurrent_checkout_only_one_wins_last_unit(client, db_session, make_user, auth_headers):
    from app.models.enums import UserRole

    product = await _make_product(db_session, stock=1)
    member_a, _ = await make_user(UserRole.MEMBER)
    member_b, _ = await make_user(UserRole.MEMBER)
    headers_a = await auth_headers(member_a)
    headers_b = await auth_headers(member_b)

    await client.post(
        "/api/v1/store/cart/items", json={"product_id": str(product.id), "quantity": 1}, headers=headers_a
    )
    await client.post(
        "/api/v1/store/cart/items", json={"product_id": str(product.id), "quantity": 1}, headers=headers_b
    )

    async def checkout(headers):
        return await client.post(
            "/api/v1/store/checkout", json={"delivery_address": "addr", "phone": "555"}, headers=headers
        )

    result_a, result_b = await asyncio.gather(checkout(headers_a), checkout(headers_b))
    statuses = sorted([result_a.status_code, result_b.status_code])
    assert statuses == [201, 409]


async def test_order_status_transitions_are_validated(client, db_session, member_user, admin_user, auth_headers):
    product = await _make_product(db_session, stock=5)
    member, _ = member_user
    admin, _ = admin_user
    member_headers = await auth_headers(member)
    admin_headers = await auth_headers(admin)

    await client.post(
        "/api/v1/store/cart/items", json={"product_id": str(product.id), "quantity": 1}, headers=member_headers
    )
    checkout = await client.post(
        "/api/v1/store/checkout", json={"delivery_address": "addr", "phone": "555"}, headers=member_headers
    )
    order_id = checkout.json()["id"]

    # Member cannot change order status.
    forbidden = await client.post(
        f"/api/v1/store/orders/{order_id}/status", json={"status": "DELIVERED"}, headers=member_headers
    )
    assert forbidden.status_code == 403

    # Cannot skip from PENDING straight to DELIVERED.
    invalid = await client.post(
        f"/api/v1/store/orders/{order_id}/status", json={"status": "DELIVERED"}, headers=admin_headers
    )
    assert invalid.status_code == 400

    valid = await client.post(
        f"/api/v1/store/orders/{order_id}/status", json={"status": "CONFIRMED"}, headers=admin_headers
    )
    assert valid.status_code == 200
    assert valid.json()["status"] == "CONFIRMED"
