"""Authentication business logic: registration, login, refresh-token
rotation with reuse detection, logout, and password reset.

Refresh token security model:
- Each issued refresh token is represented by a RefreshSession row keyed by
  its `jti`, storing only a SHA-256 fingerprint of the token (never the
  raw token).
- Refresh tokens belong to a "family" (`family_id`). Every successful
  refresh revokes the old session and issues a new one in the same family
  (rotation).
- If a refresh token is presented that has already been revoked, this is
  treated as token reuse (e.g. a stolen/replayed token) and the ENTIRE
  family is revoked, forcing re-authentication.
"""

import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestError, ConflictError, UnauthorizedError
from app.core.security import (
    TokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.enums import UserRole
from app.models.profiles import MemberProfile
from app.models.user import PasswordResetToken, RefreshSession, User
from app.services.audit_service import record_audit_log
from app.services.email_provider import get_email_provider

logger = logging.getLogger("gym.auth")


async def _generate_member_code(session: AsyncSession) -> str:
    while True:
        candidate = f"M{secrets.randbelow(900000) + 100000}"
        exists = await session.execute(select(MemberProfile.id).where(MemberProfile.member_code == candidate))
        if exists.scalar_one_or_none() is None:
            return candidate


async def register_member(session: AsyncSession, *, email: str, password: str, full_name: str) -> User:
    existing = await session.execute(select(User.id).where(User.email == email))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("An account with this email already exists")

    user = User(email=email, hashed_password=hash_password(password), role=UserRole.MEMBER, is_active=True)
    session.add(user)
    await session.flush()

    member_code = await _generate_member_code(session)
    profile = MemberProfile(user_id=user.id, full_name=full_name, member_code=member_code)
    session.add(profile)
    await record_audit_log(
        session, actor_id=user.id, action="user.register", entity_type="User", entity_id=str(user.id)
    )
    await session.commit()
    await session.refresh(user)
    return user


async def create_staff_user(
    session: AsyncSession, *, email: str, password: str, full_name: str, role: UserRole, actor_id: uuid.UUID
) -> User:
    """Admin-only path for creating TRAINER/ADMIN accounts. Never reachable
    from public registration."""
    existing = await session.execute(select(User.id).where(User.email == email))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("An account with this email already exists")

    user = User(email=email, hashed_password=hash_password(password), role=role, is_active=True)
    session.add(user)
    await session.flush()

    if role == UserRole.TRAINER:
        from app.models.profiles import TrainerProfile

        session.add(TrainerProfile(user_id=user.id, full_name=full_name))

    await record_audit_log(
        session,
        actor_id=actor_id,
        action="user.create_staff",
        entity_type="User",
        entity_id=str(user.id),
        after={"role": role.value, "email": email},
    )
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, *, email: str, password: str) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    # Constant-shape response whether the user exists or not, to avoid
    # leaking account existence via timing/error differences.
    if user is None or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")
    if not user.is_active:
        raise UnauthorizedError("Account is disabled")
    user.last_login_at = datetime.now(UTC)
    await session.commit()
    return user


async def issue_token_pair(
    session: AsyncSession, *, user: User, user_agent: str | None, ip_address: str | None
) -> tuple[str, str]:
    access_token, _ = create_access_token(subject=str(user.id), role=user.role.value)
    refresh_token, jti = create_refresh_token(subject=str(user.id), role=user.role.value)
    now = datetime.now(UTC)
    payload = decode_token(refresh_token, expected_type=TokenType.REFRESH)

    session.add(
        RefreshSession(
            user_id=user.id,
            jti=jti,
            token_hash=hash_token(refresh_token),
            family_id=payload["family"],
            revoked=False,
            created_at=now,
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
            user_agent=user_agent[:255] if user_agent else None,
            ip_address=ip_address,
        )
    )
    await session.commit()
    return access_token, refresh_token


async def _revoke_family(session: AsyncSession, family_id: str) -> None:
    await session.execute(update(RefreshSession).where(RefreshSession.family_id == family_id).values(revoked=True))


async def refresh_token_pair(
    session: AsyncSession, *, refresh_token: str, user_agent: str | None, ip_address: str | None
) -> tuple[str, str, UserRole]:
    try:
        payload = decode_token(refresh_token, expected_type=TokenType.REFRESH)
    except TokenError as exc:
        raise UnauthorizedError("Invalid or expired refresh token") from exc

    jti = payload["jti"]
    result = await session.execute(select(RefreshSession).where(RefreshSession.jti == jti))
    stored = result.scalar_one_or_none()
    if stored is None or stored.token_hash != hash_token(refresh_token):
        raise UnauthorizedError("Invalid refresh token")

    if stored.revoked:
        # Reuse of an already-rotated/revoked token: revoke the whole
        # family since this strongly suggests token theft.
        await _revoke_family(session, stored.family_id)
        await session.commit()
        raise UnauthorizedError("Refresh token reuse detected; all sessions revoked")

    if stored.expires_at < datetime.now(UTC):
        raise UnauthorizedError("Refresh token expired")

    user = await session.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Account is disabled")

    new_access_token, _ = create_access_token(subject=str(user.id), role=user.role.value)
    new_refresh_token, new_jti = create_refresh_token(
        subject=str(user.id), role=user.role.value, family_id=stored.family_id
    )
    new_payload = decode_token(new_refresh_token, expected_type=TokenType.REFRESH)

    stored.revoked = True
    stored.replaced_by_jti = new_jti
    session.add(
        RefreshSession(
            user_id=user.id,
            jti=new_jti,
            token_hash=hash_token(new_refresh_token),
            family_id=stored.family_id,
            revoked=False,
            created_at=datetime.now(UTC),
            expires_at=datetime.fromtimestamp(new_payload["exp"], tz=UTC),
            user_agent=user_agent[:255] if user_agent else None,
            ip_address=ip_address,
        )
    )
    await session.commit()
    return new_access_token, new_refresh_token, user.role


async def logout(session: AsyncSession, *, refresh_token: str) -> None:
    try:
        payload = decode_token(refresh_token, expected_type=TokenType.REFRESH)
    except TokenError:
        return  # Already unusable; logout is idempotent.
    await session.execute(update(RefreshSession).where(RefreshSession.jti == payload["jti"]).values(revoked=True))
    await session.commit()


async def logout_all(session: AsyncSession, *, user_id: uuid.UUID) -> None:
    await session.execute(update(RefreshSession).where(RefreshSession.user_id == user_id).values(revoked=True))
    await session.commit()


async def change_password(session: AsyncSession, *, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.hashed_password):
        raise BadRequestError("Current password is incorrect")
    user.hashed_password = hash_password(new_password)
    await logout_all(session, user_id=user.id)
    await record_audit_log(session, actor_id=user.id, action="user.change_password", entity_type="User")
    await session.commit()


async def request_password_reset(session: AsyncSession, *, email: str) -> str | None:
    """Returns the raw reset token only for internal use (e.g. surfacing it
    in non-production responses / sending via email). Callers must never
    log this value."""
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        return None  # Caller responds identically either way (no enumeration).

    raw_token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    session.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            used=False,
            created_at=now,
            expires_at=now + timedelta(minutes=30),
        )
    )
    await session.commit()

    try:
        await get_email_provider().send(
            to=email,
            subject=f"Reset your {settings.app_name} password",
            text=(
                "We received a request to reset your password.\n\n"
                f"Enter this code in the app's Reset Password screen:\n\n{raw_token}\n\n"
                "This code expires in 30 minutes. If you didn't request this, you can ignore this email."
            ),
        )
    except Exception:
        # Delivery failure must never surface to the caller (this endpoint
        # always returns success to avoid account enumeration) — but it
        # must be visible in logs, since it's otherwise silent.
        logger.exception("password_reset_email_failed")

    return raw_token


async def reset_password(session: AsyncSession, *, token: str, new_password: str) -> None:
    token_hash = hash_token(token)
    result = await session.execute(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    reset_row = result.scalar_one_or_none()
    if reset_row is None or reset_row.used or reset_row.expires_at < datetime.now(UTC):
        raise BadRequestError("Invalid or expired reset token")

    user = await session.get(User, reset_row.user_id)
    if user is None:
        raise BadRequestError("Invalid or expired reset token")

    user.hashed_password = hash_password(new_password)
    reset_row.used = True
    await logout_all(session, user_id=user.id)
    await record_audit_log(session, actor_id=user.id, action="user.reset_password", entity_type="User")
    await session.commit()
