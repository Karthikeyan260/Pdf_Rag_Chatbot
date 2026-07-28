from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.schemas.chat import ConversationRead
from app.schemas.dashboard import DashboardResponse, DashboardStats
from app.schemas.document import DocumentRead

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> DashboardResponse:
    docs_result = await db.execute(select(Document).where(Document.owner_id == current_user.id))
    documents = docs_result.scalars().all()

    conversations_result = await db.execute(
        select(Conversation)
        .where(Conversation.owner_id == current_user.id)
        .order_by(Conversation.created_at.desc())
        .limit(10)
    )
    conversations = conversations_result.scalars().all()

    total_conversations_result = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.owner_id == current_user.id)
    )
    total_conversations = total_conversations_result.scalar_one()

    processing_statuses = {
        DocumentStatus.QUEUED,
        DocumentStatus.VALIDATING,
        DocumentStatus.EXTRACTING,
        DocumentStatus.OCR,
        DocumentStatus.CHUNKING,
        DocumentStatus.EMBEDDING,
    }

    stats = DashboardStats(
        total_documents=len(documents),
        documents_processing=sum(1 for d in documents if d.status in processing_statuses),
        documents_done=sum(1 for d in documents if d.status == DocumentStatus.DONE),
        documents_failed=sum(1 for d in documents if d.status == DocumentStatus.FAILED),
        total_pages=sum(d.page_count for d in documents),
        total_chunks=sum(d.chunk_count for d in documents),
        total_embeddings=sum(d.embedding_count for d in documents),
        storage_used_bytes=sum(d.file_size_bytes for d in documents),
        total_conversations=total_conversations,
    )

    recent_documents = sorted(documents, key=lambda d: d.created_at, reverse=True)[:10]

    return DashboardResponse(
        stats=stats,
        recent_documents=[DocumentRead.model_validate(d) for d in recent_documents],
        recent_conversations=[ConversationRead.model_validate(c) for c in conversations],
    )
