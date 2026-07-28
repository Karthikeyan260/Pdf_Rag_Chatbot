import asyncio
import time
import uuid

from app.core.config import get_settings
from app.db.sync_session import SyncSessionLocal
from app.models.chunk import Chunk, ChunkType
from app.models.document import Document, DocumentStatus
from app.services.embeddings.factory import get_embedding_provider
from app.services.pdf_processing.chunker import chunk_document
from app.services.pdf_processing.image_extractor import extract_images
from app.services.pdf_processing.ocr import ocr_scanned_pages
from app.services.pdf_processing.progress import publish_progress
from app.services.pdf_processing.scan_detector import find_scanned_pages
from app.services.pdf_processing.storage import image_storage_dir, read_file
from app.services.pdf_processing.table_extractor import extract_tables
from app.services.pdf_processing.text_extractor import extract_pages, get_pdf_metadata
from app.services.pdf_processing.types import ChunkDraft
from app.services.pdf_processing.validator import validate_pdf_bytes
from app.services.vectorstore.base import VectorRecord

settings = get_settings()


def _publish(document_id: str, status: str, percent: int, detail: str = "") -> None:
    asyncio.run(publish_progress(document_id, status, percent, detail))


def _update_status(db, document: Document, status: DocumentStatus, percent: int, detail: str) -> None:
    document.status = status
    document.progress_percent = percent
    document.status_detail = detail
    db.commit()


async def _embed_and_store(texts: list[str], vector_ids: list[str], payloads: list[dict]) -> int:
    embedder = get_embedding_provider()
    vectors = await embedder.embed_documents(texts)

    # A fresh vector-store instance is constructed here rather than reusing the
    # request-path singleton (app.services.vectorstore.factory.get_vector_store):
    # Celery invokes this whole async phase via a new asyncio.run() per task, and an
    # httpx-based async client (Qdrant) cached across separate event loops breaks.
    if settings.vectorstore_provider == "qdrant":
        from app.services.vectorstore.qdrant_store import QdrantVectorStore

        store = QdrantVectorStore()
    elif settings.vectorstore_provider == "chroma":
        from app.services.vectorstore.chroma_store import ChromaVectorStore

        store = ChromaVectorStore()
    else:
        from app.services.vectorstore.factory import get_vector_store

        store = get_vector_store()

    await store.ensure_collection(embedder.dimension)
    records = [
        VectorRecord(id=vid, vector=vec, payload=payload)
        for vid, vec, payload in zip(vector_ids, vectors, payloads)
    ]
    await store.upsert(records)
    return len(records)


def _persist_chunks(db, document: Document, drafts: list[ChunkDraft]) -> list[Chunk]:
    temp_to_real: dict[str, uuid.UUID] = {}
    chunks: list[Chunk] = []

    parent_drafts = [d for d in drafts if d.is_parent]
    child_drafts = [d for d in drafts if not d.is_parent]

    for d in parent_drafts:
        chunk = Chunk(
            document_id=document.id,
            parent_chunk_id=None,
            chunk_type=ChunkType(d.chunk_type),
            text=d.text,
            page_number=d.page_number,
            section_title=d.section_title,
            section_path=d.section_path,
            bbox=d.bbox,
            token_count=d.token_count,
        )
        db.add(chunk)
        db.flush()
        temp_to_real[d.temp_id] = chunk.id
        chunks.append(chunk)

    for d in child_drafts:
        parent_real_id = temp_to_real.get(d.parent_temp_id) if d.parent_temp_id else None
        chunk = Chunk(
            document_id=document.id,
            parent_chunk_id=parent_real_id,
            chunk_type=ChunkType(d.chunk_type),
            text=d.text,
            page_number=d.page_number,
            section_title=d.section_title,
            section_path=d.section_path,
            bbox=d.bbox,
            token_count=d.token_count,
        )
        db.add(chunk)
        db.flush()
        temp_to_real[d.temp_id] = chunk.id
        chunks.append(chunk)

    db.commit()
    return chunks


def process_document(document_id: str) -> None:
    doc_uuid = uuid.UUID(document_id)
    start_time = time.monotonic()

    with SyncSessionLocal() as db:
        document = db.get(Document, doc_uuid)
        if document is None:
            return

        try:
            _update_status(db, document, DocumentStatus.VALIDATING, 5, "Validating file")
            _publish(document_id, "validating", 5)
            data = read_file(document.storage_path)
            validate_pdf_bytes(data, document.filename)

            _update_status(db, document, DocumentStatus.EXTRACTING, 15, "Extracting text and structure")
            _publish(document_id, "extracting", 15)
            pages = extract_pages(document.storage_path)
            document.page_count = len(pages)
            document.doc_metadata = {"pdf_metadata": get_pdf_metadata(document.storage_path)}
            db.commit()

            scanned_pages = find_scanned_pages(pages)
            if scanned_pages:
                _update_status(
                    db, document, DocumentStatus.OCR, 30, f"Running OCR on {len(scanned_pages)} scanned page(s)"
                )
                _publish(document_id, "ocr", 30)
                pages = ocr_scanned_pages(document.storage_path, pages)

            _update_status(db, document, DocumentStatus.EXTRACTING, 45, "Extracting tables and images")
            _publish(document_id, "extracting", 45)
            tables = extract_tables(document.storage_path)
            image_dir = image_storage_dir(str(document.owner_id), str(document.id))
            images = extract_images(document.storage_path, image_dir)

            _update_status(db, document, DocumentStatus.CHUNKING, 60, "Building heading-aware semantic chunks")
            _publish(document_id, "chunking", 60)
            drafts = chunk_document(pages, tables, images)
            chunks = _persist_chunks(db, document, drafts)
            document.chunk_count = len(chunks)
            db.commit()

            _update_status(db, document, DocumentStatus.EMBEDDING, 80, "Generating embeddings and indexing vectors")
            _publish(document_id, "embedding", 80)

            texts = [c.text for c in chunks]
            vector_ids = [str(c.id) for c in chunks]
            payloads = [
                {
                    "document_id": str(document.id),
                    "chunk_id": str(c.id),
                    "page_number": c.page_number,
                    "section_title": c.section_title,
                    "chunk_type": c.chunk_type.value,
                }
                for c in chunks
            ]
            embedding_count = asyncio.run(_embed_and_store(texts, vector_ids, payloads))
            for c in chunks:
                c.vector_id = str(c.id)

            document.embedding_count = embedding_count
            document.processing_time_seconds = time.monotonic() - start_time
            document.status = DocumentStatus.DONE
            document.progress_percent = 100
            document.status_detail = "Processing complete"
            db.commit()
            _publish(document_id, "done", 100, "Processing complete")

        except Exception as exc:  # noqa: BLE001 — surfaced to the user via document.status_detail
            db.rollback()
            document = db.get(Document, doc_uuid)
            if document is not None:
                document.status = DocumentStatus.FAILED
                document.status_detail = str(exc)[:1000]
                db.commit()
            _publish(document_id, "failed", document.progress_percent if document else 0, str(exc)[:500])
            raise
