from collections.abc import Sequence
from typing import Generic, TypeVar

from pydantic import BaseModel, Field
from sqlalchemy import Select, func
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class Page(BaseModel, Generic[T]):
    items: Sequence[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def create(cls, items: Sequence[T], total: int, params: PageParams) -> "Page[T]":
        pages = (total + params.page_size - 1) // params.page_size if total else 0
        return cls(items=items, total=total, page=params.page, page_size=params.page_size, pages=pages)


async def paginate(session: AsyncSession, stmt: Select, params: PageParams) -> tuple[Sequence, int]:
    total = (await session.execute(stmt.with_only_columns(func.count()).order_by(None))).scalar_one()
    result = await session.execute(stmt.offset(params.offset).limit(params.page_size))
    items = result.scalars().unique().all()
    return items, total
