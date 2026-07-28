from pydantic import BaseModel

from app.schemas.chat import ConversationRead
from app.schemas.document import DocumentRead


class DashboardStats(BaseModel):
    total_documents: int
    documents_processing: int
    documents_done: int
    documents_failed: int
    total_pages: int
    total_chunks: int
    total_embeddings: int
    storage_used_bytes: int
    total_conversations: int


class DashboardResponse(BaseModel):
    stats: DashboardStats
    recent_documents: list[DocumentRead]
    recent_conversations: list[ConversationRead]
