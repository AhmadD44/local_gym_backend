import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.gym_info import FAQ, ContactRequest, Feedback, GymOpeningHours, GymRule, GymSettings


async def get_gym_settings(session: AsyncSession) -> GymSettings:
    result = await session.execute(select(GymSettings).limit(1))
    settings_row = result.scalar_one_or_none()
    if settings_row is None:
        settings_row = GymSettings(name="Our Gym")
        session.add(settings_row)
        await session.commit()
        await session.refresh(settings_row)
    return settings_row


async def update_gym_settings(session: AsyncSession, *, data) -> GymSettings:
    settings_row = await get_gym_settings(session)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(settings_row, field, value)
    await session.commit()
    await session.refresh(settings_row)
    return settings_row


async def list_opening_hours(session: AsyncSession) -> list[GymOpeningHours]:
    result = await session.execute(select(GymOpeningHours).order_by(GymOpeningHours.day_of_week))
    return list(result.scalars().all())


async def upsert_opening_hours(session: AsyncSession, *, data) -> GymOpeningHours:
    result = await session.execute(select(GymOpeningHours).where(GymOpeningHours.day_of_week == data.day_of_week))
    row = result.scalar_one_or_none()
    if row is None:
        row = GymOpeningHours(**data.model_dump())
        session.add(row)
    else:
        for field, value in data.model_dump().items():
            setattr(row, field, value)
    await session.commit()
    await session.refresh(row)
    return row


async def list_gym_rules(session: AsyncSession) -> list[GymRule]:
    result = await session.execute(select(GymRule).order_by(GymRule.order_index))
    return list(result.scalars().all())


async def create_gym_rule(session: AsyncSession, *, data) -> GymRule:
    rule = GymRule(**data.model_dump())
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return rule


async def delete_gym_rule(session: AsyncSession, *, rule_id: uuid.UUID) -> None:
    rule = await session.get(GymRule, rule_id)
    if rule is None:
        raise NotFoundError("Rule not found")
    await session.delete(rule)
    await session.commit()


async def list_faqs(session: AsyncSession, *, active_only: bool) -> list[FAQ]:
    stmt = select(FAQ).order_by(FAQ.order_index)
    if active_only:
        stmt = stmt.where(FAQ.is_active.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_faq(session: AsyncSession, *, data) -> FAQ:
    faq = FAQ(**data.model_dump())
    session.add(faq)
    await session.commit()
    await session.refresh(faq)
    return faq


async def update_faq(session: AsyncSession, *, faq_id: uuid.UUID, data) -> FAQ:
    faq = await session.get(FAQ, faq_id)
    if faq is None:
        raise NotFoundError("FAQ not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(faq, field, value)
    await session.commit()
    await session.refresh(faq)
    return faq


async def delete_faq(session: AsyncSession, *, faq_id: uuid.UUID) -> None:
    faq = await session.get(FAQ, faq_id)
    if faq is None:
        raise NotFoundError("FAQ not found")
    await session.delete(faq)
    await session.commit()


async def create_contact_request(session: AsyncSession, *, member_id: uuid.UUID | None, data) -> ContactRequest:
    request = ContactRequest(member_id=member_id, **data.model_dump())
    session.add(request)
    await session.commit()
    await session.refresh(request)
    return request


async def list_contact_requests(session: AsyncSession) -> list[ContactRequest]:
    result = await session.execute(select(ContactRequest).order_by(ContactRequest.created_at.desc()))
    return list(result.scalars().all())


async def update_contact_status(session: AsyncSession, *, request_id: uuid.UUID, status) -> ContactRequest:
    request = await session.get(ContactRequest, request_id)
    if request is None:
        raise NotFoundError("Contact request not found")
    request.status = status
    await session.commit()
    await session.refresh(request)
    return request


async def create_feedback(session: AsyncSession, *, member_id: uuid.UUID, data) -> Feedback:
    feedback = Feedback(member_id=member_id, created_at=datetime.now(UTC), **data.model_dump())
    session.add(feedback)
    await session.commit()
    await session.refresh(feedback)
    return feedback


async def list_feedback(session: AsyncSession) -> list[Feedback]:
    result = await session.execute(select(Feedback).order_by(Feedback.created_at.desc()))
    return list(result.scalars().all())
