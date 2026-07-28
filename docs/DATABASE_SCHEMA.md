# Database Schema

PostgreSQL, managed via Alembic (`backend/alembic/versions/0001_initial.py`). SQLAlchemy models live in `backend/app/models/`.

```
users
├── id (uuid, pk)
├── email (unique, indexed)
├── hashed_password
├── full_name
├── is_active
└── created_at / updated_at

documents
├── id (uuid, pk)
├── owner_id → users.id (cascade delete)
├── filename, storage_path, file_hash (indexed — powers duplicate detection), file_size_bytes
├── page_count
├── status (enum: queued/validating/extracting/ocr/chunking/embedding/done/failed), status_detail, progress_percent
├── chunk_count, embedding_count, processing_time_seconds
├── doc_metadata (jsonb — raw PDF metadata: title/author/creation date/etc)
└── created_at / updated_at

chunks
├── id (uuid, pk)
├── document_id → documents.id (cascade delete)
├── parent_chunk_id → chunks.id, nullable, self-referential (parent/child retrieval:
│     a "parent" is a section-level chunk covering ~3000 chars for broad context;
│     "children" are ~700-char paragraph-level chunks used for precise dense/BM25
│     matching, each pointing back at its parent)
├── chunk_type (enum: text/table/figure)
├── text (the chunk content — markdown table for chunk_type=table, a `[Figure on
│     page N]` placeholder + stored image path for chunk_type=figure — Phase 2 adds
│     real image captioning here)
├── page_number, section_title, section_path (breadcrumb, e.g. "Chapter 1 > 1.2 Background")
├── bbox (jsonb, nullable — [x0,y0,x1,y1] in PDF points, used to highlight the chunk's
│     region in the viewer when its citation is clicked)
├── token_count
├── vector_id (the id used in the vector store — currently == chunks.id as a string)
└── created_at / updated_at

conversations
├── id (uuid, pk)
├── owner_id → users.id (cascade delete)
├── title
├── document_ids (uuid[] — the set of documents this conversation can retrieve from;
│     more than one enables multi-PDF chat)
└── created_at / updated_at

messages
├── id (uuid, pk)
├── conversation_id → conversations.id (cascade delete)
├── role (enum: user/assistant)
├── content
├── confidence_score (nullable — assistant messages only; mean reranker score of the
│     chunks used to answer)
├── prompt_tokens, completion_tokens, latency_ms
└── created_at / updated_at

citations
├── id (uuid, pk)
├── message_id → messages.id (cascade delete)
├── chunk_id → chunks.id (cascade delete)
├── document_id → documents.id (cascade delete, denormalized for convenient joins)
├── page_number, section_title (denormalized from the chunk at answer time)
├── confidence_score (this specific chunk's reranker score)
├── bbox (jsonb, nullable — copied from the chunk at answer time so citation history
│     doesn't require a join back to chunks just to re-render a highlight)
└── created_at / updated_at
```

## Notes

- All primary keys are UUIDv4, generated application-side (`uuid.uuid4()` as the SQLAlchemy column default) rather than DB-side, so newly-created rows have a usable `.id` before the first flush.
- `document_status`, `chunk_type`, and `message_role` are native Postgres enums (created explicitly in the migration, not inferred from the Python `Enum`).
- The vector store (Qdrant/Chroma) is the source of truth for embeddings themselves — Postgres only stores `chunks.vector_id` as the join key. There is no `embeddings` table; each provider's own storage format is used as-is (see `backend/app/services/vectorstore/`).
- `chunks.parent_chunk_id` is nullable and `ON DELETE SET NULL` rather than cascading, so deleting a child chunk never removes its parent, and if a parent were ever deleted independently its children survive as top-level chunks instead of disappearing.
