import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.chat import Conversation, ConversationParticipant, Message


async def get_or_create_conversation(
    session: AsyncSession, *, user_id: uuid.UUID, other_user_id: uuid.UUID
) -> Conversation:
    if user_id == other_user_id:
        raise BadRequestError("Cannot start a conversation with yourself")

    # Find an existing 1:1 conversation containing exactly these two users.
    stmt = (
        select(Conversation)
        .join(ConversationParticipant, ConversationParticipant.conversation_id == Conversation.id)
        .where(ConversationParticipant.user_id.in_([user_id, other_user_id]))
        .options(selectinload(Conversation.participants))
    )
    result = await session.execute(stmt)
    for convo in result.scalars().unique().all():
        participant_ids = {p.user_id for p in convo.participants}
        if participant_ids == {user_id, other_user_id}:
            return convo

    convo = Conversation()
    convo.participants.append(ConversationParticipant(user_id=user_id))
    convo.participants.append(ConversationParticipant(user_id=other_user_id))
    session.add(convo)
    await session.commit()

    result = await session.execute(
        select(Conversation).where(Conversation.id == convo.id).options(selectinload(Conversation.participants))
    )
    return result.scalar_one()


async def list_conversations_for_user(session: AsyncSession, *, user_id: uuid.UUID) -> list[Conversation]:
    stmt = (
        select(Conversation)
        .join(ConversationParticipant, ConversationParticipant.conversation_id == Conversation.id)
        .where(ConversationParticipant.user_id == user_id)
        .options(selectinload(Conversation.participants))
        .order_by(Conversation.last_message_at.desc().nulls_last())
    )
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def assert_participant(
    session: AsyncSession, *, conversation_id: uuid.UUID, user_id: uuid.UUID
) -> Conversation:
    result = await session.execute(
        select(Conversation)
        .join(ConversationParticipant, ConversationParticipant.conversation_id == Conversation.id)
        .where(Conversation.id == conversation_id, ConversationParticipant.user_id == user_id)
    )
    convo = result.scalar_one_or_none()
    if convo is None:
        raise NotFoundError("Conversation not found")
    return convo


async def list_messages(
    session: AsyncSession, *, conversation_id: uuid.UUID, before: datetime | None, limit: int
) -> list[Message]:
    stmt = select(Message).where(Message.conversation_id == conversation_id)
    if before is not None:
        stmt = stmt.where(Message.created_at < before)
    stmt = stmt.order_by(Message.created_at.desc()).limit(limit)
    result = await session.execute(stmt)
    return list(reversed(result.scalars().all()))


async def post_message(
    session: AsyncSession, *, conversation_id: uuid.UUID, sender_id: uuid.UUID, content: str
) -> Message:
    now = datetime.now(UTC)
    message = Message(conversation_id=conversation_id, sender_id=sender_id, content=content, created_at=now)
    session.add(message)
    convo = await session.get(Conversation, conversation_id)
    if convo is not None:
        convo.last_message_at = now
    await session.commit()
    await session.refresh(message)
    return message


async def mark_read(session: AsyncSession, *, conversation_id: uuid.UUID, user_id: uuid.UUID) -> None:
    result = await session.execute(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == user_id,
        )
    )
    participant = result.scalar_one_or_none()
    if participant is None:
        raise NotFoundError("Conversation not found")
    participant.last_read_at = datetime.now(UTC)
    await session.commit()
