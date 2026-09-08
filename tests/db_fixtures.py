"""Database-backed fixtures, shared by tests/integration/conftest.py and
tests/security/conftest.py (imported with `from tests.db_fixtures import
*`). Requires a running PostgreSQL (see docker-compose.yml) reachable at
TEST_DATABASE_URL / DATABASE_URL, with schema created/dropped once per
session via SQLAlchemy metadata (not Alembic — faster for tests, and the
migration file is verified separately).
"""

import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import hash_password
from app.main import app
from app.models import Base
from app.models.enums import UserRole
from app.models.profiles import MemberProfile, TrainerProfile
from app.models.user import User
from app.services.auth_service import issue_token_pair

test_engine = create_async_engine(settings.database_url, pool_pre_ping=True)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

# `from tests.db_fixtures import *` (used by tests/integration/conftest.py
# and tests/security/conftest.py) does NOT import underscore-prefixed names
# by default — without this __all__, the autouse `_setup_schema` and
# `_clean_tables` fixtures silently never run in those directories, so the
# test database schema never gets created and every DB-touching test fails
# with "relation ... does not exist".
__all__ = [
    "_setup_schema",
    "_clean_tables",
    "db_session",
    "client",
    "make_user",
    "auth_headers",
    "member_user",
    "trainer_user",
    "admin_user",
]


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _setup_schema():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables():
    yield
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    # Every test's httpx ASGITransport client reports the same fake client
    # IP, so Redis-backed rate-limit counters (and anything else keyed in
    # Redis, e.g. WS abuse counters) would otherwise leak across unrelated
    # tests within the same session — e.g. a handful of tests each calling
    # /auth/login legitimately once could add up and trip the 5/minute
    # login limiter for a later, unrelated test. Flush just the configured
    # test Redis logical DB (REDIS_URL points at db 15 by default here, not
    # the dev db 0) between tests for isolation.
    await get_redis().flushdb()


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    """Each request gets its own AsyncSession/connection (like production
    connection pooling), so concurrent requests genuinely race at the
    database level — required for the stock/capacity concurrency tests."""

    async def _override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _create_user(db_session, *, role: UserRole, email: str | None = None, password: str = "SuperSecret123!"):
    email = email or f"{role.value.lower()}-{uuid.uuid4().hex[:8]}@example.com"
    user = User(email=email, hashed_password=hash_password(password), role=role, is_active=True)
    db_session.add(user)
    await db_session.flush()

    if role == UserRole.MEMBER:
        db_session.add(
            MemberProfile(
                user_id=user.id, full_name="Test Member", member_code=f"M{uuid.uuid4().int % 900000 + 100000}"
            )
        )
    elif role == UserRole.TRAINER:
        db_session.add(TrainerProfile(user_id=user.id, full_name="Test Trainer"))

    await db_session.commit()
    await db_session.refresh(user)
    return user, password


@pytest_asyncio.fixture
async def make_user(db_session):
    async def _make(role: UserRole, **kwargs):
        return await _create_user(db_session, role=role, **kwargs)

    return _make


@pytest_asyncio.fixture
async def auth_headers(db_session):
    async def _headers_for(user: User) -> dict:
        access, _ = await issue_token_pair(db_session, user=user, user_agent="pytest", ip_address="127.0.0.1")
        return {"Authorization": f"Bearer {access}"}

    return _headers_for


@pytest_asyncio.fixture
async def member_user(db_session):
    return await _create_user(db_session, role=UserRole.MEMBER)


@pytest_asyncio.fixture
async def trainer_user(db_session):
    return await _create_user(db_session, role=UserRole.TRAINER)


@pytest_asyncio.fixture
async def admin_user(db_session):
    return await _create_user(db_session, role=UserRole.ADMIN)
