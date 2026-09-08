"""Role-based access control and IDOR/BOLA regression tests."""


async def test_member_cannot_access_admin_dashboard(client, member_user, auth_headers):
    user, _ = member_user
    headers = await auth_headers(user)
    resp = await client.get("/api/v1/admin/dashboard", headers=headers)
    assert resp.status_code == 403


async def test_member_cannot_create_membership_plan(client, member_user, auth_headers):
    user, _ = member_user
    headers = await auth_headers(user)
    resp = await client.post(
        "/api/v1/memberships/plans",
        json={"name": "Gold", "duration_days": 30, "price": "50.00"},
        headers=headers,
    )
    assert resp.status_code == 403


async def test_member_cannot_confirm_own_membership_payment(client, member_user, auth_headers, db_session):
    from app.models.membership import MembershipPlan

    user, _ = member_user
    headers = await auth_headers(user)

    plan = MembershipPlan(name="Gold", duration_days=30, price="50.00")
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)

    subscribe = await client.post("/api/v1/memberships/subscribe", json={"plan_id": str(plan.id)}, headers=headers)
    assert subscribe.status_code == 201
    subscription_id = subscribe.json()["id"]

    confirm = await client.post(f"/api/v1/memberships/{subscription_id}/confirm-payment", json={}, headers=headers)
    # Only admins can confirm; a member hitting this route must be forbidden.
    assert confirm.status_code == 403


async def test_member_cannot_view_another_members_profile(client, db_session, make_user, auth_headers):
    member_a, _ = await make_user_role(make_user, "MEMBER")
    member_b, _ = await make_user_role(make_user, "MEMBER")
    headers = await auth_headers(member_a)

    from sqlalchemy import select

    from app.models.profiles import MemberProfile

    result = await db_session.execute(select(MemberProfile).where(MemberProfile.user_id == member_b.id))
    profile_b = result.scalar_one()

    resp = await client.get(f"/api/v1/members/{profile_b.id}", headers=headers)
    # Must look like "not found", not a 403 that would confirm the id exists.
    assert resp.status_code == 404


async def test_trainer_cannot_view_unassigned_member(client, db_session, make_user, auth_headers):
    trainer, _ = await make_user_role(make_user, "TRAINER")
    member, _ = await make_user_role(make_user, "MEMBER")
    headers = await auth_headers(trainer)

    from sqlalchemy import select

    from app.models.profiles import MemberProfile

    result = await db_session.execute(select(MemberProfile).where(MemberProfile.user_id == member.id))
    profile = result.scalar_one()

    resp = await client.get(f"/api/v1/members/{profile.id}", headers=headers)
    assert resp.status_code == 404


async def test_trainer_can_view_assigned_member(client, db_session, make_user, auth_headers, admin_user):
    trainer, _ = await make_user_role(make_user, "TRAINER")
    member, _ = await make_user_role(make_user, "MEMBER")

    admin, _ = admin_user
    admin_headers = await auth_headers(admin)

    from sqlalchemy import select

    from app.models.profiles import MemberProfile, TrainerProfile

    member_profile = (
        await db_session.execute(select(MemberProfile).where(MemberProfile.user_id == member.id))
    ).scalar_one()
    trainer_profile = (
        await db_session.execute(select(TrainerProfile).where(TrainerProfile.user_id == trainer.id))
    ).scalar_one()

    assign = await client.post(
        "/api/v1/members/assign-trainer",
        json={"member_id": str(member_profile.id), "trainer_id": str(trainer_profile.id)},
        headers=admin_headers,
    )
    assert assign.status_code == 200

    trainer_headers = await auth_headers(trainer)
    resp = await client.get(f"/api/v1/members/{member_profile.id}", headers=trainer_headers)
    assert resp.status_code == 200


async def test_unauthenticated_request_rejected(client):
    resp = await client.get("/api/v1/members/me")
    assert resp.status_code == 401


async def make_user_role(make_user, role_str: str):
    from app.models.enums import UserRole

    return await make_user(UserRole(role_str))
