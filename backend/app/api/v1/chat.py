import json
import time
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.citation import Citation
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.message import Message, MessageRole
from app.models.user import User
from app.schemas.chat import ConversationCreate, ConversationRead, MessageCreate, MessageRead
from app.services.embeddings.factory import get_embedding_provider
from app.services.llm.factory import get_llm_provider
from app.services.reranker.factory import get_reranker_provider
from app.services.retrieval.agent_graph import run_retrieval
from app.services.retrieval.graph_runner import build_chat_messages, build_citations
from app.services.vectorstore.factory import get_vector_store

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/conversations", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationRead:
    result = await db.execute(
        select(Document.id).where(Document.owner_id == current_user.id, Document.id.in_(payload.document_ids))
    )
    owned_ids = {row[0] for row in result.all()}
    if owned_ids != set(payload.document_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more documents were not found")

    conversation = Conversation(
        owner_id=current_user.id,
        title=payload.title or "New conversation",
        document_ids=payload.document_ids,
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return ConversationRead.model_validate(conversation)


@router.get("/conversations", response_model=list[ConversationRead])
async def list_conversations(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[ConversationRead]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.owner_id == current_user.id)
        .order_by(Conversation.created_at.desc())
    )
    return [ConversationRead.model_validate(c) for c in result.scalars().all()]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageRead])
async def list_messages(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MessageRead]:
    conversation = await _get_owned_conversation(db, conversation_id, current_user)
    result = await db.execute(
        select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at)
    )
    messages = result.scalars().unique().all()
    return [MessageRead.model_validate(m) for m in messages]


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    conversation = await _get_owned_conversation(db, conversation_id, current_user)

    history_result = await db.execute(
        select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at)
    )
    history = [{"role": m.role.value, "content": m.content} for m in history_result.scalars().all()]

    user_message = Message(conversation_id=conversation.id, role=MessageRole.USER, content=payload.content)
    db.add(user_message)
    await db.commit()

    document_ids = [str(d) for d in conversation.document_ids]

    async def event_stream() -> AsyncIterator[str]:
        start = time.monotonic()
        llm = get_llm_provider()

        retrieval = await run_retrieval(
            llm=llm,
            embedder=get_embedding_provider(),
            store=get_vector_store(),
            reranker=get_reranker_provider(),
            db=db,
            question=payload.content,
            history=history,
            document_ids=document_ids,
        )

        messages = build_chat_messages(retrieval["context"], payload.content, history)

        full_answer = ""
        async for token in llm.stream(messages):
            full_answer += token
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

        latency_ms = int((time.monotonic() - start) * 1000)
        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=full_answer,
            confidence_score=retrieval["confidence"],
            latency_ms=latency_ms,
        )
        db.add(assistant_message)
        await db.flush()

        citation_dicts = build_citations(retrieval["chunks"])
        for c in citation_dicts:
            db.add(
                Citation(
                    message_id=assistant_message.id,
                    chunk_id=uuid.UUID(c["chunk_id"]),
                    document_id=uuid.UUID(c["document_id"]),
                    page_number=c["page_number"],
                    section_title=c["section_title"],
                    confidence_score=c["confidence_score"],
                    bbox=c["bbox"],
                )
            )
        await db.commit()

        yield f"data: {json.dumps({'type': 'done', 'message_id': str(assistant_message.id), 'confidence': retrieval['confidence'], 'citations': citation_dicts})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


async def _get_owned_conversation(db: AsyncSession, conversation_id: uuid.UUID, current_user: User) -> Conversation:
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.owner_id == current_user.id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation
