from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import get_member_profile_for_user, require_role
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.dashboard import DigitalMemberCard, MemberDashboardResponse
from app.services.dashboard_service import get_digital_member_card, get_member_dashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/me", response_model=MemberDashboardResponse, summary="My member dashboard")
async def my_dashboard(db: AsyncSession = Depends(get_db), user: User = Depends(require_role(UserRole.MEMBER))):
    profile = await get_member_profile_for_user(user, db)
    return await get_member_dashboard(db, member_id=profile.id)


@router.get(
    "/card",
    response_model=DigitalMemberCard,
    summary="My digital member card (informational only, no check-in)",
)
async def my_card(db: AsyncSession = Depends(get_db), user: User = Depends(require_role(UserRole.MEMBER))):
    profile = await get_member_profile_for_user(user, db)
    return await get_digital_member_card(db, member=profile)
