# Enterprise AI Document Intelligence Platform (Phase 1 — MVP Core)

A full-stack RAG platform for asking natural-language questions over uploaded PDFs, with grounded, cited, streamed answers.

This is **Phase 1**: a complete, working end-to-end slice — auth, upload, an async PDF pipeline (text/OCR/tables/images/heading-aware semantic chunking), a hybrid-retrieval + rerank + LangGraph agent, streaming chat with clickable citations that jump-and-highlight in a split-screen PDF viewer, and a basic analytics dashboard. Advanced features (AI summaries, document insights/NER, image/chart QA, voice chat, export, full-text search, document comparison, timeline, knowledge graph) are intentionally deferred to Phase 2 — see [Roadmap](#phase-2-roadmap).

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind, shadcn/ui, Framer Motion, react-pdf, Zustand |
| Backend | FastAPI, SQLAlchemy (async), LangChain/LangGraph, Celery + Redis |
| Database | PostgreSQL |
| Vector store | Qdrant (live), Chroma (live, dev), Pinecone (Phase 2 stub) |
| LLM | Gemini 2.5 (live), OpenAI/Claude/Llama (Phase 2 stubs) |
| Embeddings | BAAI BGE-M3 (live), Jina/Voyage/OpenAI (Phase 2 stubs) |
| Reranker | BGE reranker v2-m3 (live), Cohere (Phase 2 stub) |

Every provider category sits behind a common interface (`app/services/<category>/base.py`) selected by a factory reading `app/core/config.py`. Swapping providers is an env var change (`LLM_PROVIDER`, `EMBEDDING_PROVIDER`, `RERANKER_PROVIDER`, `VECTORSTORE_PROVIDER`) — Phase 2 stub adapters already have the correct method signatures, they just need their SDK calls filled in.

## Architecture

```
Upload → validate → store → hash-dedupe → extract text (PyMuPDF) → detect scanned pages
  → OCR (pytesseract) → extract tables (pdfplumber) → extract images → detect headings/sections
  → heading+paragraph-aware semantic chunking (parent/child, table/figure chunks)
  → embed (BGE-M3) → index (Qdrant) → done                    [async, Celery]

Question → query rewrite → multi-query expansion → hybrid search (dense + BM25)
  → Reciprocal Rank Fusion → cross-encoder rerank (BGE) → context compression
  → LLM (Gemini, streamed) → citations (page/section/chunk/confidence)          [LangGraph agent]
```

See [docs/API.md](docs/API.md) for the full endpoint reference and [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) for the data model.

## Quickstart (Docker)

```bash
cp .env.example .env
# Edit .env and set GEMINI_API_KEY (https://aistudio.google.com/apikey) — the LLM won't work without it.

docker compose -f docker/docker-compose.yml up -d --build
```

- Frontend: http://localhost:3000
- Backend API docs (Swagger): http://localhost:8000/docs
- Qdrant dashboard: http://localhost:6333/dashboard

Sign up, upload `sample_pdfs/demo_annual_report.pdf`, watch it process on the dashboard, open it, and ask something like *"What was the net profit in 2024?"* — this PDF has that answer only inside a table, exercising the table-extraction + table-QA path end to end.

The first request that touches BGE-M3/BGE-reranker will download the model weights (a few GB) — expect the first document's processing and the first chat message to be slow.

## Local development (without Docker)

**Backend**
```bash
cd backend
python -m venv .venv && .venv/Scripts/activate   # or `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp ../.env.example ../.env   # then edit DATABASE_URL/REDIS_URL/QDRANT_URL to point at localhost services
alembic upgrade head
uvicorn app.main:app --reload
```
In a second terminal, run the background worker (required for document processing):
```bash
celery -A app.workers.celery_app worker --loglevel=info --pool=solo
```
You'll need Postgres, Redis, and Qdrant reachable at the URLs in `.env` — easiest is `docker compose -f docker/docker-compose.yml up -d postgres redis qdrant`.

**Frontend**
```bash
cd frontend
npm install --legacy-peer-deps   # some deps haven't published React 19 peer ranges yet
cp .env.example .env.local
npm run dev
```

## Tests

```bash
cd backend
pytest tests/unit           # pure unit tests — chunking, RRF merge, compression, validation, auth tokens; no infra needed
pytest tests/integration    # API flow tests — needs Postgres + Redis reachable (see Quickstart); auto-skip if not
pytest                      # both
```

## Provider swapping

Set in `.env` (see `.env.example` for every key):
```
LLM_PROVIDER=gemini|openai|claude|llama
EMBEDDING_PROVIDER=bge_m3|jina|voyage|openai
RERANKER_PROVIDER=bge|cohere
VECTORSTORE_PROVIDER=qdrant|chroma|pinecone
```
Only `gemini`/`bge_m3`/`bge`/`qdrant`+`chroma` are implemented in Phase 1; the others are typed stub adapters (`app/services/<category>/<name>.py`) that raise `NotImplementedError` with a comment on exactly what SDK call to add.

## Phase 2 roadmap

Deferred deliberately to keep Phase 1 shippable and reviewable: AI summaries (executive/technical/bullet/key-takeaways/action-items), document insights (NER: people/orgs/dates/locations/topics), a dedicated table-QA UI (table extraction already exists in the pipeline — Phase 1 chat can already answer from tables, this is about a dedicated UI), multimodal image/chart QA, voice chat, chat export (PDF/DOCX/Markdown), full-text search UI, document comparison, timeline extraction, knowledge graph, plus filling in the OpenAI/Claude/Llama, Jina/Voyage/OpenAI-embedding, Cohere, and Pinecone stub adapters.

## Known limitations (Phase 1)

- BM25 is rebuilt from the DB per chat request, scoped to the conversation's document(s) — fine at MVP scale; a persistent sparse index is the scale-up path.
- Celery tasks run their own event loop per task; the vector-store client is instantiated fresh per pipeline run rather than reusing the FastAPI-side singleton, to avoid reusing an httpx-based async client across event loops (see the comment in `app/services/pdf_processing/pipeline.py`).
- No virus-scanning hook is wired to a real scanner — `validator.py` is the integration point for one.
