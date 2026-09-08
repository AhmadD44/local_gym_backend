"""One-off CLI to bootstrap the first ADMIN account from environment
variables. This is the only way to create an ADMIN without already having
one — there is no public API path to become an admin.

Usage:
    python -m scripts.create_admin
"""

import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User


async def main() -> None:
    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(User).where(User.email == settings.bootstrap_admin_email))
        if existing.scalar_one_or_none() is not None:
            print(f"Admin '{settings.bootstrap_admin_email}' already exists; nothing to do.")
            return

        user = User(
            email=settings.bootstrap_admin_email,
            hashed_password=hash_password(settings.bootstrap_admin_password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        print(f"Created admin account: {settings.bootstrap_admin_email}")
        print("Log in and change the bootstrap password immediately.")


if __name__ == "__main__":
    asyncio.run(main())
