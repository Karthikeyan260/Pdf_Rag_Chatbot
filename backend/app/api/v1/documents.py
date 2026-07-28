import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.schemas.document import DocumentRead, DocumentUploadResponse
from app.services.pdf_processing.hashing import sha256_bytes
from app.services.pdf_processing.storage import save_upload
from app.services.pdf_processing.validator import PDFValidationError, validate_pdf_bytes
from app.workers.tasks import process_document_task

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=list[DocumentUploadResponse], status_code=status.HTTP_201_CREATED)
async def upload_documents(
    files: list[UploadFile],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DocumentUploadResponse]:
    responses: list[DocumentUploadResponse] = []

    for file in files:
        data = await file.read()
        try:
            validate_pdf_bytes(data, file.filename or "upload.pdf")
        except PDFValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        file_hash = sha256_bytes(data)
        existing = await db.execute(
            select(Document).where(Document.owner_id == current_user.id, Document.file_hash == file_hash)
        )
        duplicate = existing.scalar_one_or_none()
        if duplicate:
            responses.append(DocumentUploadResponse(document=DocumentRead.model_validate(duplicate), duplicate_of=duplicate.id))
            continue

        storage_path = save_upload(data, str(current_user.id), file.filename or "upload.pdf")
        document = Document(
            owner_id=current_user.id,
            filename=file.filename or "upload.pdf",
            storage_path=storage_path,
            file_hash=file_hash,
            file_size_bytes=len(data),
            status=DocumentStatus.QUEUED,
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)

        process_document_task.delay(str(document.id))
        responses.append(DocumentUploadResponse(document=DocumentRead.model_validate(document)))

    return responses


@router.get("", response_model=list[DocumentRead])
async def list_documents(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[DocumentRead]:
    result = await db.execute(
        select(Document).where(Document.owner_id == current_user.id).order_by(Document.created_at.desc())
    )
    return [DocumentRead.model_validate(d) for d in result.scalars().all()]


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentRead:
    document = await _get_owned_document(db, document_id, current_user)
    return DocumentRead.model_validate(document)


@router.get("/{document_id}/file")
async def get_document_file(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    document = await _get_owned_document(db, document_id, current_user)
    return FileResponse(document.storage_path, media_type="application/pdf", filename=document.filename)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    document = await _get_owned_document(db, document_id, current_user)

    from app.services.vectorstore.factory import get_vector_store

    store = get_vector_store()
    await store.delete_document(str(document.id))

    await db.delete(document)
    await db.commit()


async def _get_owned_document(db: AsyncSession, document_id: uuid.UUID, current_user: User) -> Document:
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.owner_id == current_user.id)
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document
