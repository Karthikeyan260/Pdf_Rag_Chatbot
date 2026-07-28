import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.document import CitationRead


class ConversationCreate(BaseModel):
    document_ids: list[uuid.UUID]
    title: str | None = None


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    document_ids: list[uuid.UUID]
    created_at: datetime


class MessageCreate(BaseModel):
    content: str


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    confidence_score: float | None
    created_at: datetime
    citations: list[CitationRead] = []
