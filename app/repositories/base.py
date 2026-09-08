import uuid
from typing import Generic, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Page, PageParams, paginate

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """Thin generic CRUD repository for simple lookup-style entities
    (categories, exercises, FAQs, ...). Domain logic with invariants
    (stock, capacity, payment state machines) lives in services instead,
    since a generic repository cannot safely express those rules."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id_: uuid.UUID) -> ModelT | None:
        return await self.session.get(self.model, id_)

    async def list_all(self, stmt: Select | None = None) -> list[ModelT]:
        stmt = stmt if stmt is not None else select(self.model)
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def paginate(self, stmt: Select, params: PageParams) -> Page[ModelT]:
        items, total = await paginate(self.session, stmt, params)
        return Page.create(items, total, params)

    def add(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        await self.session.delete(instance)
