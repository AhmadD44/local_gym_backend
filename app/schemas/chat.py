import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import IDModel


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class MessageRead(IDModel):
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    content: str
    created_at: datetime


class ConversationParticipantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: uuid.UUID
    last_read_at: datetime | None


class ConversationCreate(BaseModel):
    other_user_id: uuid.UUID


class ConversationRead(IDModel):
    last_message_at: datetime | None
    participants: list[ConversationParticipantRead]
    created_at: datetime
