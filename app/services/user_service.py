import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.pagination import Page, PageParams
from app.models.profiles import MemberProfile, TrainerMemberAssignment, TrainerProfile
from app.models.user import User
from app.services.audit_service import record_audit_log

MEMBER_SORT_FIELDS = {"full_name": MemberProfile.full_name, "created_at": MemberProfile.created_at}


async def search_members(
    session: AsyncSession,
    *,
    params: PageParams,
    search: str | None,
    is_active: bool | None,
    sort_by: str,
    sort_desc: bool,
) -> Page:
    stmt = (
        select(MemberProfile)
        .join(User, MemberProfile.user_id == User.id)
        .options(selectinload(MemberProfile.user))
    )
    if search:
        like = f"%{search}%"
        stmt = stmt.where((MemberProfile.full_name.ilike(like)) | (User.email.ilike(like)))
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))

    sort_col = MEMBER_SORT_FIELDS.get(sort_by, MemberProfile.created_at)
    stmt = stmt.order_by(sort_col.desc() if sort_desc else sort_col.asc())

    from app.core.pagination import paginate

    items, total = await paginate(session, stmt, params)
    return Page.create(items, total, params)


async def set_member_active_status(
    session: AsyncSession, *, member: MemberProfile, is_active: bool, actor_id: uuid.UUID
) -> MemberProfile:
    user = await session.get(User, member.user_id)
    if user is None:
        raise NotFoundError("Member not found")
    before = {"is_active": user.is_active}
    user.is_active = is_active
    await record_audit_log(
        session,
        actor_id=actor_id,
        action="member.set_active" if is_active else "member.deactivate",
        entity_type="MemberProfile",
        entity_id=str(member.id),
        before=before,
        after={"is_active": is_active},
    )
    await session.commit()
    await session.refresh(member)
    return member


async def assign_trainer(
    session: AsyncSession, *, member_id: uuid.UUID, trainer_id: uuid.UUID, actor_id: uuid.UUID
) -> TrainerMemberAssignment:
    member = await session.get(MemberProfile, member_id)
    if member is None:
        raise NotFoundError("Member not found")
    trainer = await session.get(TrainerProfile, trainer_id)
    if trainer is None or not trainer.is_active:
        raise NotFoundError("Trainer not found")

    existing = await session.execute(
        select(TrainerMemberAssignment).where(
            TrainerMemberAssignment.member_id == member_id, TrainerMemberAssignment.active.is_(True)
        )
    )
    current = existing.scalar_one_or_none()
    if current is not None:
        if current.trainer_id == trainer_id:
            return current
        current.active = False
        current.unassigned_at = datetime.now(UTC)

    assignment = TrainerMemberAssignment(
        trainer_id=trainer_id, member_id=member_id, active=True, assigned_at=datetime.now(UTC)
    )
    session.add(assignment)
    await record_audit_log(
        session,
        actor_id=actor_id,
        action="member.assign_trainer",
        entity_type="TrainerMemberAssignment",
        entity_id=str(member_id),
        after={"trainer_id": str(trainer_id)},
    )
    await session.commit()
    await session.refresh(assignment)
    return assignment


async def unassign_trainer(session: AsyncSession, *, member_id: uuid.UUID, actor_id: uuid.UUID) -> None:
    result = await session.execute(
        select(TrainerMemberAssignment).where(
            TrainerMemberAssignment.member_id == member_id, TrainerMemberAssignment.active.is_(True)
        )
    )
    current = result.scalar_one_or_none()
    if current is None:
        raise BadRequestError("Member has no active trainer assignment")
    current.active = False
    current.unassigned_at = datetime.now(UTC)
    await record_audit_log(
        session,
        actor_id=actor_id,
        action="member.unassign_trainer",
        entity_type="TrainerMemberAssignment",
        entity_id=str(member_id),
    )
    await session.commit()


async def list_assigned_members(session: AsyncSession, *, trainer_id: uuid.UUID) -> list[MemberProfile]:
    stmt = (
        select(MemberProfile)
        .join(TrainerMemberAssignment, TrainerMemberAssignment.member_id == MemberProfile.id)
        .where(TrainerMemberAssignment.trainer_id == trainer_id, TrainerMemberAssignment.active.is_(True))
    )
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def list_trainers(session: AsyncSession, *, active_only: bool = True) -> list[TrainerProfile]:
    stmt = select(TrainerProfile)
    if active_only:
        stmt = stmt.where(TrainerProfile.is_active.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())
