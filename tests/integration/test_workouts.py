from sqlalchemy import select

from app.models.enums import UserRole
from app.models.exercise import Exercise
from app.models.profiles import MemberProfile, TrainerProfile


async def _assign(client, db_session, admin_headers, member_user, trainer_user):
    member_profile = (
        await db_session.execute(select(MemberProfile).where(MemberProfile.user_id == member_user.id))
    ).scalar_one()
    trainer_profile = (
        await db_session.execute(select(TrainerProfile).where(TrainerProfile.user_id == trainer_user.id))
    ).scalar_one()
    resp = await client.post(
        "/api/v1/members/assign-trainer",
        json={"member_id": str(member_profile.id), "trainer_id": str(trainer_profile.id)},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    return member_profile, trainer_profile


async def test_trainer_can_create_program_for_assigned_member_only(
    client, db_session, member_user, trainer_user, admin_user, auth_headers
):
    member, _ = member_user
    trainer, _ = trainer_user
    admin, _ = admin_user
    admin_headers = await auth_headers(admin)
    trainer_headers = await auth_headers(trainer)

    exercise = Exercise(name="Squat", muscle_group="Legs")
    db_session.add(exercise)
    await db_session.commit()
    await db_session.refresh(exercise)

    member_profile, _ = await _assign(client, db_session, admin_headers, member, trainer)

    payload = {
        "member_id": str(member_profile.id),
        "name": "Strength Block",
        "days": [
            {
                "day_number": 1,
                "name": "Day 1",
                "exercises": [{"exercise_id": str(exercise.id), "sets": 3, "reps": 10}],
            }
        ],
    }
    resp = await client.post("/api/v1/workouts/programs", json=payload, headers=trainer_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["days"][0]["exercises"][0]["sets"] == 3


async def test_trainer_cannot_create_program_for_unassigned_member(
    client, db_session, member_user, trainer_user, auth_headers
):
    member, _ = member_user
    trainer, _ = trainer_user
    trainer_headers = await auth_headers(trainer)

    member_profile = (
        await db_session.execute(select(MemberProfile).where(MemberProfile.user_id == member.id))
    ).scalar_one()

    payload = {"member_id": str(member_profile.id), "name": "Should Fail", "days": []}
    resp = await client.post("/api/v1/workouts/programs", json=payload, headers=trainer_headers)
    assert resp.status_code == 403


async def test_member_cannot_see_another_members_program(
    client, db_session, member_user, trainer_user, admin_user, make_user, auth_headers
):
    member, _ = member_user
    trainer, _ = trainer_user
    admin, _ = admin_user
    admin_headers = await auth_headers(admin)
    trainer_headers = await auth_headers(trainer)

    member_profile, _ = await _assign(client, db_session, admin_headers, member, trainer)

    payload = {"member_id": str(member_profile.id), "name": "Plan A", "days": []}
    created = await client.post("/api/v1/workouts/programs", json=payload, headers=trainer_headers)
    program_id = created.json()["id"]

    other_member, _ = await make_user(UserRole.MEMBER)
    other_headers = await auth_headers(other_member)

    resp = await client.get(f"/api/v1/workouts/programs/{program_id}", headers=other_headers)
    assert resp.status_code == 404
