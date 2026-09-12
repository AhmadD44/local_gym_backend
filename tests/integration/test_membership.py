from sqlalchemy import select

from app.models.membership import MembershipPlan
from app.models.profiles import MemberProfile


async def _make_plan(db_session):
    plan = MembershipPlan(name="Gold", duration_days=30, price="99.99")
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return plan


async def test_subscribe_creates_pending_subscription(client, db_session, member_user, auth_headers):
    plan = await _make_plan(db_session)
    user, _ = member_user
    headers = await auth_headers(user)

    resp = await client.post("/api/v1/memberships/subscribe", json={"plan_id": str(plan.id)}, headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "PENDING"
    assert body["payment_status"] == "PENDING"


async def test_admin_confirm_payment_activates_membership(
    client, db_session, member_user, admin_user, auth_headers
):
    plan = await _make_plan(db_session)
    member, _ = member_user
    admin, _ = admin_user
    member_headers = await auth_headers(member)
    admin_headers = await auth_headers(admin)

    subscribe = await client.post(
        "/api/v1/memberships/subscribe", json={"plan_id": str(plan.id)}, headers=member_headers
    )
    subscription_id = subscribe.json()["id"]

    confirm = await client.post(
        f"/api/v1/memberships/{subscription_id}/confirm-payment", json={}, headers=admin_headers
    )
    assert confirm.status_code == 200
    body = confirm.json()
    assert body["status"] == "ACTIVE"
    assert body["payment_status"] == "PAID"
    assert body["expiry_date"] is not None


async def test_cannot_double_subscribe(client, db_session, member_user, auth_headers):
    plan = await _make_plan(db_session)
    user, _ = member_user
    headers = await auth_headers(user)

    first = await client.post("/api/v1/memberships/subscribe", json={"plan_id": str(plan.id)}, headers=headers)
    assert first.status_code == 201
    second = await client.post("/api/v1/memberships/subscribe", json={"plan_id": str(plan.id)}, headers=headers)
    assert second.status_code == 409


async def test_admin_can_list_pending_subscriptions(client, db_session, member_user, admin_user, auth_headers):
    plan = await _make_plan(db_session)
    member, _ = member_user
    admin, _ = admin_user
    member_headers = await auth_headers(member)
    admin_headers = await auth_headers(admin)

    subscribe = await client.post(
        "/api/v1/memberships/subscribe", json={"plan_id": str(plan.id)}, headers=member_headers
    )
    subscription_id = subscribe.json()["id"]

    pending = await client.get(
        "/api/v1/memberships/subscriptions", params={"status_filter": "PENDING"}, headers=admin_headers
    )
    assert pending.status_code == 200
    body = pending.json()
    assert body["total"] == 1
    listed = body["items"][0]
    assert listed["id"] == subscription_id
    profile = (
        await db_session.execute(select(MemberProfile).where(MemberProfile.user_id == member.id))
    ).scalar_one()
    assert listed["member"]["id"] == str(profile.id)

    await client.post(f"/api/v1/memberships/{subscription_id}/confirm-payment", json={}, headers=admin_headers)

    still_pending = await client.get(
        "/api/v1/memberships/subscriptions", params={"status_filter": "PENDING"}, headers=admin_headers
    )
    assert still_pending.json()["total"] == 0

    active = await client.get(
        "/api/v1/memberships/subscriptions", params={"status_filter": "ACTIVE"}, headers=admin_headers
    )
    assert active.json()["total"] == 1


async def test_list_subscriptions_requires_admin(client, member_user, auth_headers):
    headers = await auth_headers(member_user[0])
    resp = await client.get("/api/v1/memberships/subscriptions", headers=headers)
    assert resp.status_code == 403


async def test_extend_requires_admin(client, db_session, member_user, admin_user, auth_headers):
    plan = await _make_plan(db_session)
    member, _ = member_user
    admin, _ = admin_user
    member_headers = await auth_headers(member)
    admin_headers = await auth_headers(admin)

    subscribe = await client.post(
        "/api/v1/memberships/subscribe", json={"plan_id": str(plan.id)}, headers=member_headers
    )
    subscription_id = subscribe.json()["id"]
    await client.post(f"/api/v1/memberships/{subscription_id}/confirm-payment", json={}, headers=admin_headers)

    forbidden = await client.post(
        f"/api/v1/memberships/{subscription_id}/extend", json={"additional_days": 10}, headers=member_headers
    )
    assert forbidden.status_code == 403

    allowed = await client.post(
        f"/api/v1/memberships/{subscription_id}/extend", json={"additional_days": 10}, headers=admin_headers
    )
    assert allowed.status_code == 200
