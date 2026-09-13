"""Exercise real route matching without a database or authentication server."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints import workouts
from app.core.database import get_db
from app.core.permissions import get_current_active_user
from app.models.enums import UserRole


@pytest.fixture
def workout_api(monkeypatch):
    app = FastAPI()
    app.include_router(workouts.router, prefix="/api/v1")
    member = SimpleNamespace(id=uuid.uuid4())
    user = SimpleNamespace(id=uuid.uuid4(), role=UserRole.MEMBER)
    db = object()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_active_user] = lambda: user
    profile = AsyncMock(return_value=member)
    listing = AsyncMock(return_value=[])
    detail = AsyncMock(side_effect=HTTPException(status_code=404, detail="Program not found"))
    monkeypatch.setattr(workouts, "get_member_profile_for_user", profile)
    monkeypatch.setattr(workouts.workout_service, "list_programs_for_member", listing)
    monkeypatch.setattr(workouts.workout_service, "get_program_detail", detail)
    return app, member, db, listing, detail


async def test_member_programs_me_returns_list_instead_of_uuid_error(workout_api):
    app, member, db, listing, detail = workout_api
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/workouts/programs/me")
    assert response.status_code == 200, response.text
    assert response.json() == []
    listing.assert_awaited_once_with(db, member_id=member.id)
    detail.assert_not_awaited()


async def test_program_uuid_still_reaches_detail_handler(workout_api):
    app, _, db, listing, detail = workout_api
    program_id = uuid.uuid4()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/workouts/programs/{program_id}")
    assert response.status_code == 404
    detail.assert_awaited_once_with(db, program_id=program_id)
    listing.assert_not_awaited()


async def test_invalid_program_id_still_fails_validation(workout_api):
    app, _, _, listing, detail = workout_api
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/workouts/programs/not-a-uuid")
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["path", "program_id"]
    listing.assert_not_awaited()
    detail.assert_not_awaited()
