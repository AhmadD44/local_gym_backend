import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_admin
from app.schemas.promotion import PromotionCreate, PromotionRead, PromotionUpdate
from app.services import promotion_service

router = APIRouter(prefix="/promotions", tags=["promotions"])


@router.get("/active", response_model=list[PromotionRead], summary="List currently active promotions")
async def list_active(db: AsyncSession = Depends(get_db)):
    promos = await promotion_service.list_active_promotions(db)
    return [promotion_service.promotion_to_read(p) for p in promos]


@router.get(
    "",
    response_model=list[PromotionRead],
    dependencies=[Depends(require_admin)],
    summary="List all promotions (admin only)",
)
async def list_all(db: AsyncSession = Depends(get_db)):
    promos = await promotion_service.list_all_promotions(db)
    return [promotion_service.promotion_to_read(p) for p in promos]


@router.post(
    "",
    response_model=PromotionRead,
    status_code=201,
    dependencies=[Depends(require_admin)],
    summary="Create a promotion (admin only)",
)
async def create_promotion(payload: PromotionCreate, db: AsyncSession = Depends(get_db)):
    promo = await promotion_service.create_promotion(db, data=payload)
    return promotion_service.promotion_to_read(promo)


@router.patch(
    "/{promotion_id}",
    response_model=PromotionRead,
    dependencies=[Depends(require_admin)],
    summary="Update a promotion (admin only)",
)
async def update_promotion(promotion_id: uuid.UUID, payload: PromotionUpdate, db: AsyncSession = Depends(get_db)):
    promo = await promotion_service.update_promotion(db, promotion_id=promotion_id, data=payload)
    return promotion_service.promotion_to_read(promo)
