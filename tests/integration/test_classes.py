import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models.enums import UserRole
from app.models.gym_class import GymClass
from app.models.profiles import TrainerProfile


async def _make_class(db_session, *, capacity=1, trainer_user=None):
    if trainer_user is None:
        from app.core.security import hash_password
        from app.models.user import User

        u = User(
            email="trainer-fixture@example.com", hashed_password=hash_password("x" * 12), role=UserRole.TRAINER
        )
        db_session.add(u)
        await db_session.flush()
        trainer_user = u

    result = await db_session.execute(select(TrainerProfile).where(TrainerProfile.user_id == trainer_user.id))
    trainer_profile = result.scalar_one_or_none()
    if trainer_profile is None:
        trainer_profile = TrainerProfile(user_id=trainer_user.id, full_name="Coach")
        db_session.add(trainer_profile)
        await db_session.flush()

    start = datetime.now(UTC) + timedelta(hours=1)
    gym_class = GymClass(
        name="Yoga",
        trainer_id=trainer_profile.id,
        capacity=capacity,
        start_time=start,
        end_time=start + timedelta(hours=1),
    )
    db_session.add(gym_class)
    await db_session.commit()
    await db_session.refresh(gym_class)
    return gym_class


async def test_book_class_success(client, db_session, trainer_user, member_user, auth_headers):
    trainer, _ = trainer_user
    gym_class = await _make_class(db_session, capacity=5, trainer_user=trainer)
    member, _ = member_user
    headers = await auth_headers(member)

    resp = await client.post(f"/api/v1/classes/{gym_class.id}/book", headers=headers)
    assert resp.status_code == 201
    assert resp.json()["status"] == "BOOKED"


async def test_duplicate_booking_rejected(client, db_session, trainer_user, member_user, auth_headers):
    trainer, _ = trainer_user
    gym_class = await _make_class(db_session, capacity=5, trainer_user=trainer)
    member, _ = member_user
    headers = await auth_headers(member)

    await client.post(f"/api/v1/classes/{gym_class.id}/book", headers=headers)
    second = await client.post(f"/api/v1/classes/{gym_class.id}/book", headers=headers)
    assert second.status_code == 409


async def test_full_class_rejects_booking(client, db_session, trainer_user, make_user, auth_headers):
    trainer, _ = trainer_user
    gym_class = await _make_class(db_session, capacity=1, trainer_user=trainer)
    member_a, _ = await make_user(UserRole.MEMBER)
    member_b, _ = await make_user(UserRole.MEMBER)

    headers_a = await auth_headers(member_a)
    headers_b = await auth_headers(member_b)

    first = await client.post(f"/api/v1/classes/{gym_class.id}/book", headers=headers_a)
    assert first.status_code == 201
    second = await client.post(f"/api/v1/classes/{gym_class.id}/book", headers=headers_b)
    assert second.status_code == 409


async def test_concurrent_booking_only_one_gets_last_seat(
    client, db_session, trainer_user, make_user, auth_headers
):
    trainer, _ = trainer_user
    gym_class = await _make_class(db_session, capacity=1, trainer_user=trainer)
    member_a, _ = await make_user(UserRole.MEMBER)
    member_b, _ = await make_user(UserRole.MEMBER)
    headers_a = await auth_headers(member_a)
    headers_b = await auth_headers(member_b)

    async def book(headers):
        return await client.post(f"/api/v1/classes/{gym_class.id}/book", headers=headers)

    result_a, result_b = await asyncio.gather(book(headers_a), book(headers_b))
    statuses = sorted([result_a.status_code, result_b.status_code])
    assert statuses == [201, 409]


async def test_cancel_booking_frees_seat(client, db_session, trainer_user, make_user, auth_headers):
    trainer, _ = trainer_user
    gym_class = await _make_class(db_session, capacity=1, trainer_user=trainer)
    member_a, _ = await make_user(UserRole.MEMBER)
    member_b, _ = await make_user(UserRole.MEMBER)
    headers_a = await auth_headers(member_a)
    headers_b = await auth_headers(member_b)

    booking = await client.post(f"/api/v1/classes/{gym_class.id}/book", headers=headers_a)
    booking_id = booking.json()["id"]

    cancel = await client.post(f"/api/v1/classes/bookings/{booking_id}/cancel", headers=headers_a)
    assert cancel.status_code == 200

    rebook = await client.post(f"/api/v1/classes/{gym_class.id}/book", headers=headers_b)
    assert rebook.status_code == 201
