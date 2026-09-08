import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import get_current_active_user
from app.core.rate_limit import RateLimiter
from app.models.user import User
from app.schemas.chat import ConversationCreate, ConversationRead, MessageCreate, MessageRead
from app.services import chat_service
from app.websocket.chat_ws import publish_message

router = APIRouter(prefix="/conversations", tags=["chat"])


@router.get("", response_model=list[ConversationRead], summary="List my conversations")
async def list_conversations(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_active_user)):
    return await chat_service.list_conversations_for_user(db, user_id=user.id)


@router.post("", response_model=ConversationRead, status_code=201, summary="Start (or reuse) a 1:1 conversation")
async def create_conversation(
    payload: ConversationCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_active_user)
):
    return await chat_service.get_or_create_conversation(db, user_id=user.id, other_user_id=payload.other_user_id)


@router.get(
    "/{conversation_id}/messages",
    response_model=list[MessageRead],
    summary="List messages in a conversation (paginated by `before`)",
)
async def list_messages(
    conversation_id: uuid.UUID,
    before: datetime | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    await chat_service.assert_participant(db, conversation_id=conversation_id, user_id=user.id)
    return await chat_service.list_messages(db, conversation_id=conversation_id, before=before, limit=limit)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageRead,
    status_code=201,
    summary="Send a message (also broadcast over the conversation's WebSocket)",
    dependencies=[Depends(RateLimiter(times=30, seconds=60, scope="chat_send"))],
)
async def send_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    await chat_service.assert_participant(db, conversation_id=conversation_id, user_id=user.id)
    message = await chat_service.post_message(
        db, conversation_id=conversation_id, sender_id=user.id, content=payload.content
    )
    await publish_message(conversation_id, MessageRead.model_validate(message))
    return message


@router.post("/{conversation_id}/read", summary="Mark a conversation as read up to now")
async def mark_read(
    conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_active_user)
):
    await chat_service.mark_read(db, conversation_id=conversation_id, user_id=user.id)
    return {"message": "Marked as read"}
