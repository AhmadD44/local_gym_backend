import uuid

from fastapi import APIRouter, Depends, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BadRequestError
from app.core.pagination import Page, PageParams
from app.core.permissions import (
    get_accessible_member_profile,
    get_current_active_user,
    get_member_profile_for_user,
    require_admin,
)
from app.models.profiles import MemberProfile
from app.models.user import User
from app.schemas.profiles import (
    AssignTrainerRequest,
    MemberAdminUpdate,
    MemberProfileRead,
    MemberProfileUpdate,
    MemberWithAccountRead,
)
from app.services import user_service
from app.utils.uploads import validate_and_store_image

router = APIRouter(prefix="/members", tags=["members"])

_SORTABLE_FIELDS = {"full_name", "created_at"}


@router.get("/me", response_model=MemberProfileRead, summary="Get my member profile")
async def get_my_profile(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_active_user)):
    return await get_member_profile_for_user(user, db)


@router.patch("/me", response_model=MemberProfileRead, summary="Update my member profile")
async def update_my_profile(
    payload: MemberProfileUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    profile = await get_member_profile_for_user(user, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.post("/me/photo", response_model=MemberProfileRead, summary="Upload my profile photo")
async def upload_my_photo(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    profile = await get_member_profile_for_user(user, db)
    url = await validate_and_store_image(file, folder="member-photos")
    profile.photo_url = url
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get(
    "",
    response_model=Page[MemberWithAccountRead],
    dependencies=[Depends(require_admin)],
    summary="Search/list members (admin only)",
)
async def list_members(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    is_active: bool | None = None,
    sort_by: str = Query("created_at"),
    sort_desc: bool = True,
):
    if sort_by not in _SORTABLE_FIELDS:
        raise BadRequestError(f"sort_by must be one of {sorted(_SORTABLE_FIELDS)}")
    result = await user_service.search_members(
        db,
        params=PageParams(page=page, page_size=page_size),
        search=search,
        is_active=is_active,
        sort_by=sort_by,
        sort_desc=sort_desc,
    )
    items = [
        MemberWithAccountRead.model_validate(
            {
                **MemberProfileRead.model_validate(m).model_dump(),
                "email": m.user.email,
                "is_active": m.user.is_active,
            }
        )
        for m in result.items
    ]
    return Page.create(items, result.total, PageParams(page=page, page_size=page_size))


@router.get("/{member_id}", response_model=MemberProfileRead, summary="Get a member's profile")
async def get_member(
    member_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_active_user)
):
    return await get_accessible_member_profile(member_id, current_user=user, db=db)


@router.patch(
    "/{member_id}",
    response_model=MemberProfileRead,
    dependencies=[Depends(require_admin)],
    summary="Admin update of a member profile (including activation status)",
)
async def admin_update_member(
    member_id: uuid.UUID,
    payload: MemberAdminUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    profile = await db.get(MemberProfile, member_id)
    if profile is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Member not found")

    updates = payload.model_dump(exclude_unset=True)
    is_active = updates.pop("is_active", None)
    for field, value in updates.items():
        setattr(profile, field, value)
    if is_active is not None:
        await user_service.set_member_active_status(db, member=profile, is_active=is_active, actor_id=admin.id)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.post(
    "/assign-trainer",
    dependencies=[Depends(require_admin)],
    summary="Assign a trainer to a member (admin only)",
)
async def assign_trainer(
    payload: AssignTrainerRequest, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)
):
    assignment = await user_service.assign_trainer(
        db, member_id=payload.member_id, trainer_id=payload.trainer_id, actor_id=admin.id
    )
    return {"id": assignment.id, "trainer_id": assignment.trainer_id, "member_id": assignment.member_id}


@router.delete(
    "/{member_id}/trainer",
    dependencies=[Depends(require_admin)],
    summary="Unassign a member's current trainer (admin only)",
)
async def unassign_trainer(
    member_id: uuid.UUID, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)
):
    await user_service.unassign_trainer(db, member_id=member_id, actor_id=admin.id)
    return {"message": "Trainer unassigned"}
