import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BadRequestError
from app.core.permissions import get_accessible_member_profile, get_member_profile_for_user, require_role
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.progress import (
    BodyMeasurementCreate,
    BodyMeasurementRead,
    MemberAchievementRead,
    PersonalRecordCreate,
    PersonalRecordRead,
    ProgressPhotoCreate,
    ProgressPhotoRead,
)
from app.services import progress_service
from app.utils.uploads import validate_and_store_image

router = APIRouter(prefix="/progress", tags=["progress"])

_STAFF = require_role(UserRole.ADMIN, UserRole.TRAINER)


async def _resolve_member_id(member_id: uuid.UUID | None, db: AsyncSession, user: User) -> uuid.UUID:
    if user.role == UserRole.MEMBER:
        profile = await get_member_profile_for_user(user, db)
        return profile.id
    if member_id is None:
        raise BadRequestError("member_id is required for trainer/admin requests")
    profile = await get_accessible_member_profile(member_id, current_user=user, db=db)
    return profile.id


@router.get("/measurements", response_model=list[BodyMeasurementRead], summary="List body measurements")
async def list_measurements(
    member_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.MEMBER, UserRole.TRAINER, UserRole.ADMIN)),
):
    resolved = await _resolve_member_id(member_id, db, user)
    return await progress_service.list_body_measurements(db, member_id=resolved)


@router.post(
    "/measurements",
    response_model=BodyMeasurementRead,
    status_code=201,
    summary="Record a body measurement (self or trainer for an assigned member)",
)
async def add_measurement(
    payload: BodyMeasurementCreate,
    member_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.MEMBER, UserRole.TRAINER, UserRole.ADMIN)),
):
    resolved = await _resolve_member_id(member_id, db, user)
    return await progress_service.add_body_measurement(db, member_id=resolved, data=payload, recorded_by=user.id)


@router.get("/photos", response_model=list[ProgressPhotoRead], summary="List progress photos")
async def list_photos(
    member_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.MEMBER, UserRole.TRAINER, UserRole.ADMIN)),
):
    resolved = await _resolve_member_id(member_id, db, user)
    return await progress_service.list_progress_photos(db, member_id=resolved)


@router.post(
    "/photos", response_model=ProgressPhotoRead, status_code=201, summary="Upload a progress photo (member)"
)
async def add_photo(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.MEMBER)),
):
    profile = await get_member_profile_for_user(user, db)
    url = await validate_and_store_image(file, folder="progress-photos")
    data = ProgressPhotoCreate(photo_url=url, taken_at=datetime.now(UTC))
    return await progress_service.add_progress_photo(db, member_id=profile.id, data=data)


@router.get("/records", response_model=list[PersonalRecordRead], summary="List personal records")
async def list_records(
    member_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.MEMBER, UserRole.TRAINER, UserRole.ADMIN)),
):
    resolved = await _resolve_member_id(member_id, db, user)
    return await progress_service.list_personal_records(db, member_id=resolved)


@router.post("/records", response_model=PersonalRecordRead, status_code=201, summary="Add a personal record")
async def add_record(
    payload: PersonalRecordCreate,
    member_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.MEMBER, UserRole.TRAINER, UserRole.ADMIN)),
):
    resolved = await _resolve_member_id(member_id, db, user)
    return await progress_service.add_personal_record(db, member_id=resolved, data=payload)


@router.get("/achievements", response_model=list[MemberAchievementRead], summary="List my achievements")
async def list_achievements(
    member_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.MEMBER, UserRole.TRAINER, UserRole.ADMIN)),
):
    resolved = await _resolve_member_id(member_id, db, user)
    return await progress_service.list_member_achievements(db, member_id=resolved)
