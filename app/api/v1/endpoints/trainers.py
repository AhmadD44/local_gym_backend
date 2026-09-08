from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import get_current_active_user, get_trainer_profile_for_user, require_role
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.profiles import MemberProfileRead, TrainerProfileRead, TrainerProfileUpdate
from app.services import user_service
from app.utils.uploads import validate_and_store_image

router = APIRouter(prefix="/trainers", tags=["trainers"])


@router.get("", response_model=list[TrainerProfileRead], summary="List active trainers")
async def list_trainers(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_active_user)):
    return await user_service.list_trainers(db)


@router.get("/me", response_model=TrainerProfileRead, summary="Get my trainer profile")
async def get_my_trainer_profile(
    db: AsyncSession = Depends(get_db), user: User = Depends(require_role(UserRole.TRAINER))
):
    return await get_trainer_profile_for_user(user, db)


@router.patch("/me", response_model=TrainerProfileRead, summary="Update my trainer profile")
async def update_my_trainer_profile(
    payload: TrainerProfileUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.TRAINER)),
):
    profile = await get_trainer_profile_for_user(user, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.post("/me/photo", response_model=TrainerProfileRead, summary="Upload my trainer profile photo")
async def upload_my_trainer_photo(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.TRAINER)),
):
    profile = await get_trainer_profile_for_user(user, db)
    url = await validate_and_store_image(file, folder="trainer-photos")
    profile.photo_url = url
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get(
    "/me/members",
    response_model=list[MemberProfileRead],
    summary="List members currently assigned to me",
)
async def list_my_members(
    db: AsyncSession = Depends(get_db), user: User = Depends(require_role(UserRole.TRAINER))
):
    trainer_profile = await get_trainer_profile_for_user(user, db)
    return await user_service.list_assigned_members(db, trainer_id=trainer_profile.id)
