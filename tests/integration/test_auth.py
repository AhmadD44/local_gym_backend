async def test_register_creates_member_and_ignores_role_field(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newmember@example.com",
            "password": "SuperSecret123!",
            "full_name": "New Member",
            "role": "ADMIN",  # must be silently ignored
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body and "refresh_token" in body
    assert body["role"] == "MEMBER"

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["role"] == "MEMBER"


async def test_login_wrong_password_rejected(client, member_user):
    user, _password = member_user
    resp = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "wrong-password"})
    assert resp.status_code == 401


async def test_login_disabled_account_rejected(client, db_session, member_user):
    user, password = member_user
    user.is_active = False
    await db_session.commit()
    resp = await client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    assert resp.status_code == 401


async def test_login_success_and_refresh_rotation(client, member_user):
    user, password = member_user
    login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["role"] == "MEMBER"

    refreshed = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]
    assert new_tokens["role"] == "MEMBER"


async def test_refresh_token_reuse_is_detected_and_revokes_family(client, member_user):
    user, password = member_user
    login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    original_refresh = login.json()["refresh_token"]

    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": original_refresh})
    assert first.status_code == 200
    rotated_refresh = first.json()["refresh_token"]

    # Reusing the already-rotated (now revoked) token must fail...
    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": original_refresh})
    assert reuse.status_code == 401

    # ...and must have revoked the whole family, including the token that
    # replaced it.
    after_reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": rotated_refresh})
    assert after_reuse.status_code == 401


async def test_logout_revokes_refresh_token(client, member_user):
    user, password = member_user
    login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    refresh_token = login.json()["refresh_token"]

    logout = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout.status_code == 200

    retry = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert retry.status_code == 401


async def test_change_password_requires_correct_current_password(client, member_user, auth_headers):
    user, password = member_user
    headers = await auth_headers(user)
    resp = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "wrong", "new_password": "AnotherSecret123!"},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_forgot_and_reset_password_flow(client, member_user):
    user, _password = member_user
    forgot = await client.post("/api/v1/auth/forgot-password", json={"email": user.email})
    assert forgot.status_code == 200
    token = forgot.json().get("debug_reset_token")
    assert token, "debug token should be present in DEBUG test mode"

    reset = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "BrandNewPass123!"}
    )
    assert reset.status_code == 200

    login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "BrandNewPass123!"})
    assert login.status_code == 200
