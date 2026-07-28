import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentStatus


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    status: DocumentStatus
    status_detail: str | None
    progress_percent: int
    page_count: int
    chunk_count: int
    embedding_count: int
    processing_time_seconds: float
    file_size_bytes: int
    created_at: datetime


class DocumentUploadResponse(BaseModel):
    document: DocumentRead
    duplicate_of: uuid.UUID | None = None


class CitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    page_number: int
    section_title: str | None
    confidence_score: float
    bbox: list[float] | None = None


class ChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str
    chunk_type: str
    page_number: int
    section_title: str | None
    bbox: list[float] | None
