import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import get_member_profile_for_user, require_admin, require_role
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.gym_info import (
    ContactRequestCreate,
    ContactRequestRead,
    ContactRequestStatusUpdate,
    FAQCreate,
    FAQRead,
    FAQUpdate,
    FeedbackCreate,
    FeedbackRead,
    GymRuleCreate,
    GymRuleRead,
    GymSettingsRead,
    GymSettingsUpdate,
    OpeningHoursRead,
    OpeningHoursUpdate,
)
from app.services import gym_info_service

router = APIRouter(tags=["gym-info"])


@router.get("/gym/settings", response_model=GymSettingsRead, summary="Get gym information")
async def get_settings(db: AsyncSession = Depends(get_db)):
    return await gym_info_service.get_gym_settings(db)


@router.patch(
    "/gym/settings",
    response_model=GymSettingsRead,
    dependencies=[Depends(require_admin)],
    summary="Update gym information (admin only)",
)
async def update_settings(payload: GymSettingsUpdate, db: AsyncSession = Depends(get_db)):
    return await gym_info_service.update_gym_settings(db, data=payload)


@router.get("/gym/opening-hours", response_model=list[OpeningHoursRead], summary="Get opening hours")
async def get_opening_hours(db: AsyncSession = Depends(get_db)):
    return await gym_info_service.list_opening_hours(db)


@router.put(
    "/gym/opening-hours",
    response_model=OpeningHoursRead,
    dependencies=[Depends(require_admin)],
    summary="Upsert opening hours for a day (admin only)",
)
async def set_opening_hours(payload: OpeningHoursUpdate, db: AsyncSession = Depends(get_db)):
    return await gym_info_service.upsert_opening_hours(db, data=payload)


@router.get("/gym/rules", response_model=list[GymRuleRead], summary="List gym rules")
async def get_rules(db: AsyncSession = Depends(get_db)):
    return await gym_info_service.list_gym_rules(db)


@router.post(
    "/gym/rules",
    response_model=GymRuleRead,
    status_code=201,
    dependencies=[Depends(require_admin)],
    summary="Create a gym rule (admin only)",
)
async def create_rule(payload: GymRuleCreate, db: AsyncSession = Depends(get_db)):
    return await gym_info_service.create_gym_rule(db, data=payload)


@router.delete(
    "/gym/rules/{rule_id}", dependencies=[Depends(require_admin)], summary="Delete a gym rule (admin only)"
)
async def delete_rule(rule_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await gym_info_service.delete_gym_rule(db, rule_id=rule_id)
    return {"message": "Rule deleted"}


@router.get("/faqs", response_model=list[FAQRead], summary="List FAQs")
async def get_faqs(db: AsyncSession = Depends(get_db), active_only: bool = True):
    return await gym_info_service.list_faqs(db, active_only=active_only)


@router.post(
    "/faqs",
    response_model=FAQRead,
    status_code=201,
    dependencies=[Depends(require_admin)],
    summary="Create a FAQ (admin only)",
)
async def create_faq(payload: FAQCreate, db: AsyncSession = Depends(get_db)):
    return await gym_info_service.create_faq(db, data=payload)


@router.patch(
    "/faqs/{faq_id}",
    response_model=FAQRead,
    dependencies=[Depends(require_admin)],
    summary="Update a FAQ (admin only)",
)
async def update_faq(faq_id: uuid.UUID, payload: FAQUpdate, db: AsyncSession = Depends(get_db)):
    return await gym_info_service.update_faq(db, faq_id=faq_id, data=payload)


@router.delete("/faqs/{faq_id}", dependencies=[Depends(require_admin)], summary="Delete a FAQ (admin only)")
async def delete_faq(faq_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await gym_info_service.delete_faq(db, faq_id=faq_id)
    return {"message": "FAQ deleted"}


@router.post(
    "/contact",
    response_model=ContactRequestRead,
    status_code=201,
    summary="Submit a contact request (public, no authentication required)",
)
async def submit_contact(payload: ContactRequestCreate, db: AsyncSession = Depends(get_db)):
    return await gym_info_service.create_contact_request(db, member_id=None, data=payload)


@router.get(
    "/contact",
    response_model=list[ContactRequestRead],
    dependencies=[Depends(require_admin)],
    summary="List contact requests (admin only)",
)
async def list_contact(db: AsyncSession = Depends(get_db)):
    return await gym_info_service.list_contact_requests(db)


@router.patch(
    "/contact/{request_id}/status",
    response_model=ContactRequestRead,
    dependencies=[Depends(require_admin)],
    summary="Update a contact request's status (admin only)",
)
async def update_contact_status(
    request_id: uuid.UUID, payload: ContactRequestStatusUpdate, db: AsyncSession = Depends(get_db)
):
    return await gym_info_service.update_contact_status(db, request_id=request_id, status=payload.status)


@router.post("/feedback", response_model=FeedbackRead, status_code=201, summary="Submit feedback (member only)")
async def submit_feedback(
    payload: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.MEMBER)),
):
    profile = await get_member_profile_for_user(user, db)
    return await gym_info_service.create_feedback(db, member_id=profile.id, data=payload)


@router.get(
    "/feedback",
    response_model=list[FeedbackRead],
    dependencies=[Depends(require_admin)],
    summary="List feedback (admin only)",
)
async def list_feedback(db: AsyncSession = Depends(get_db)):
    return await gym_info_service.list_feedback(db)
