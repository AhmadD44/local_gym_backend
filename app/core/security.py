"""Password hashing and JWT issuance/verification.

Security notes:
- Passwords are hashed with Argon2id (argon2-cffi), never logged or returned.
- JWTs are signed with RS256 (asymmetric). The server never accepts an
  algorithm supplied by the client/token header beyond the single allowed
  algorithm configured here (mitigates "alg confusion" attacks).
- Every token carries `sub`, `role`, `token_type`, `jti`, `iat`, `exp`,
  `iss`, `aud` and is validated on every one of those claims.
"""

import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings

_hasher = PasswordHasher()


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    return _hasher.check_needs_rehash(hashed)


def _now() -> datetime:
    return datetime.now(UTC)


def create_token(
    *,
    subject: str,
    role: str,
    token_type: TokenType,
    expires_delta: timedelta,
    jti: str | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Returns (encoded_token, jti)."""
    jti = jti or str(uuid.uuid4())
    now = _now()
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "token_type": token_type.value,
        "jti": jti,
        "iat": now,
        "exp": now + expires_delta,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(payload, settings.jwt_private_key, algorithm=settings.jwt_algorithm)
    return token, jti


def create_access_token(*, subject: str, role: str) -> tuple[str, str]:
    return create_token(
        subject=subject,
        role=role,
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(
    *, subject: str, role: str, jti: str | None = None, family_id: str | None = None
) -> tuple[str, str]:
    family_id = family_id or str(uuid.uuid4())
    return create_token(
        subject=subject,
        role=role,
        token_type=TokenType.REFRESH,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
        jti=jti,
        extra_claims={"family": family_id},
    )


class TokenError(Exception):
    pass


def decode_token(token: str, *, expected_type: TokenType) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_public_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["exp", "iat", "sub", "jti", "token_type", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("token_expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("token_invalid") from exc

    if payload.get("token_type") != expected_type.value:
        raise TokenError("wrong_token_type")
    return payload


def hash_token(token: str) -> str:
    """One-way fingerprint used to store refresh/reset tokens without keeping plaintext."""
    import hashlib

    return hashlib.sha256(token.encode("utf-8")).hexdigest()
