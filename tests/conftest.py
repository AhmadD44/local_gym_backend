"""Shared test bootstrap: environment variables and JWT keys.

Applies to ALL tests (unit/integration/security) because `app.core.config
.settings` and `app.core.security` read these at import time. Database
fixtures (schema setup, sessions, HTTP client, test users) live in
`tests/db_fixtures.py` and are only pulled into `tests/integration/` and
`tests/security/` via their own conftest.py — pure unit tests must not
require a running PostgreSQL/Redis instance.
"""

import os
from pathlib import Path

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get("TEST_DATABASE_URL", "postgresql+asyncpg://gym:gym@localhost:5432/gym_test"),
)
os.environ.setdefault("REDIS_URL", os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/15"))
os.environ.setdefault("JWT_ISSUER", "gym-backend-test")
os.environ.setdefault("JWT_AUDIENCE", "gym-mobile-app-test")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "20")
os.environ.setdefault("STORAGE_BACKEND", "local")
os.environ.setdefault("STORAGE_LOCAL_DIR", "./.test_uploads")

_TEST_KEY_DIR = Path(__file__).parent / ".test_secrets"


def _ensure_test_keys() -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    _TEST_KEY_DIR.mkdir(exist_ok=True)
    private_path = _TEST_KEY_DIR / "jwt_private.pem"
    public_path = _TEST_KEY_DIR / "jwt_public.pem"
    if not private_path.exists():
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_path.write_bytes(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        public_path.write_bytes(
            key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        )
    os.environ["JWT_PRIVATE_KEY_PATH"] = str(private_path)
    os.environ["JWT_PUBLIC_KEY_PATH"] = str(public_path)


_ensure_test_keys()
