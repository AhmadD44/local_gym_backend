import time
from datetime import timedelta

import jwt
import pytest

from app.core.security import (
    TokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("CorrectHorseBattery1!")
    assert hashed != "CorrectHorseBattery1!"
    assert verify_password("CorrectHorseBattery1!", hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_roundtrip():
    token, jti = create_access_token(subject="user-1", role="MEMBER")
    payload = decode_token(token, expected_type=TokenType.ACCESS)
    assert payload["sub"] == "user-1"
    assert payload["role"] == "MEMBER"
    assert payload["jti"] == jti


def test_refresh_token_has_family_claim():
    token, jti = create_refresh_token(subject="user-1", role="MEMBER")
    payload = decode_token(token, expected_type=TokenType.REFRESH)
    assert "family" in payload
    assert payload["jti"] == jti


def test_wrong_token_type_rejected():
    token, _ = create_access_token(subject="user-1", role="MEMBER")
    with pytest.raises(TokenError):
        decode_token(token, expected_type=TokenType.REFRESH)


def test_expired_token_rejected():
    token, _ = create_token(
        subject="user-1", role="MEMBER", token_type=TokenType.ACCESS, expires_delta=timedelta(seconds=-1)
    )
    with pytest.raises(TokenError):
        decode_token(token, expected_type=TokenType.ACCESS)


def test_wrong_issuer_rejected():
    from app.core.config import settings

    now = time.time()
    bad_token = jwt.encode(
        {
            "sub": "user-1",
            "role": "MEMBER",
            "token_type": "access",
            "jti": "x",
            "iat": now,
            "exp": now + 60,
            "iss": "someone-else",
            "aud": settings.jwt_audience,
        },
        settings.jwt_private_key,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(TokenError):
        decode_token(bad_token, expected_type=TokenType.ACCESS)


def test_wrong_audience_rejected():
    from app.core.config import settings

    now = time.time()
    bad_token = jwt.encode(
        {
            "sub": "user-1",
            "role": "MEMBER",
            "token_type": "access",
            "jti": "x",
            "iat": now,
            "exp": now + 60,
            "iss": settings.jwt_issuer,
            "aud": "someone-elses-app",
        },
        settings.jwt_private_key,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(TokenError):
        decode_token(bad_token, expected_type=TokenType.ACCESS)


def test_algorithm_confusion_rejected():
    """A token signed with 'none' or an unexpected algorithm must never be
    accepted, even if claims otherwise look valid."""
    now = time.time()
    forged = jwt.encode(
        {"sub": "user-1", "role": "ADMIN", "token_type": "access", "jti": "x", "iat": now, "exp": now + 60},
        key="",
        algorithm="none",
    )
    with pytest.raises(TokenError):
        decode_token(forged, expected_type=TokenType.ACCESS)
