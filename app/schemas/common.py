import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class IDModel(ORMModel):
    id: uuid.UUID


class TimestampedModel(IDModel):
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    message: str
