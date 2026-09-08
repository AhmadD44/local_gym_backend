"""Authentication + authorization dependencies.

Role checks (`require_role`) are necessary but not sufficient: most
endpoints additionally call an ownership helper from this module (e.g.
`get_accessible_member_profile`) so a MEMBER can only ever reach their own
data and a TRAINER can only reach members currently assigned to them. This
is the app's IDOR/BOLA defense — never assume authentication alone implies
authorization for a specific resource.
"""

import uuid
from collections.abc import Callable

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import TokenError, TokenType, decode_token
from app.models.enums import UserRole
from app.models.profiles import MemberProfile, TrainerMemberAssignment, TrainerProfile
from app.models.user import User


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_token(token, expected_type=TokenType.ACCESS)
    except TokenError as exc:
        raise UnauthorizedError(str(exc)) from exc

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Invalid token subject") from exc

    user = await db.get(User, user_id)
    if user is None:
        raise UnauthorizedError("User not found")
    if not user.is_active:
        raise UnauthorizedError("Account is disabled")
    # Defense in depth: if the user's role changed after the token was
    # issued, trust the current DB role rather than the (stale) token claim.
    if payload.get("role") != user.role.value:
        raise UnauthorizedError("Token role is stale, please re-authenticate")
    return user


async def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    return user


def require_role(*roles: UserRole) -> Callable:
    async def _checker(user: User = Depends(get_current_active_user)) -> User:
        if user.role not in roles:
            raise ForbiddenError(f"Requires one of roles: {', '.join(r.value for r in roles)}")
        return user

    return _checker


require_admin = require_role(UserRole.ADMIN)
require_trainer = require_role(UserRole.TRAINER)
require_member = require_role(UserRole.MEMBER)
require_staff = require_role(UserRole.ADMIN, UserRole.TRAINER)


async def get_member_profile_for_user(user: User, db: AsyncSession) -> MemberProfile:
    result = await db.execute(select(MemberProfile).where(MemberProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise ForbiddenError("No member profile associated with this account")
    return profile


async def get_trainer_profile_for_user(user: User, db: AsyncSession) -> TrainerProfile:
    result = await db.execute(select(TrainerProfile).where(TrainerProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise ForbiddenError("No trainer profile associated with this account")
    return profile


async def is_member_assigned_to_trainer(db: AsyncSession, *, trainer_id: uuid.UUID, member_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(TrainerMemberAssignment.id).where(
            TrainerMemberAssignment.trainer_id == trainer_id,
            TrainerMemberAssignment.member_id == member_id,
            TrainerMemberAssignment.active.is_(True),
        )
    )
    return result.scalar_one_or_none() is not None


async def get_accessible_member_profile(
    member_id: uuid.UUID,
    *,
    current_user: User,
    db: AsyncSession,
) -> MemberProfile:
    """Load a MemberProfile by id, enforcing:
    - ADMIN: unrestricted access.
    - MEMBER: only their own profile.
    - TRAINER: only members currently assigned to them.
    Raises ForbiddenError (not 404) is intentionally avoided to not leak
    resource existence in a way that differs between "doesn't exist" and
    "not yours" — both surface as 404 to an unauthorized caller.
    """
    from app.core.exceptions import NotFoundError

    profile = await db.get(MemberProfile, member_id)
    if profile is None:
        raise NotFoundError("Member not found")

    if current_user.role == UserRole.ADMIN:
        return profile
    if current_user.role == UserRole.MEMBER:
        if profile.user_id != current_user.id:
            raise NotFoundError("Member not found")
        return profile
    if current_user.role == UserRole.TRAINER:
        trainer_profile = await get_trainer_profile_for_user(current_user, db)
        if not await is_member_assigned_to_trainer(db, trainer_id=trainer_profile.id, member_id=profile.id):
            raise NotFoundError("Member not found")
        return profile
    raise ForbiddenError()
