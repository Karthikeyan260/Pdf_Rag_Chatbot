# Deployment Guide

## Docker Compose (single-host)

This is what `docker/docker-compose.yml` sets up — good for a demo/staging box, not a multi-node production deployment.

```bash
cp .env.example .env      # fill in GEMINI_API_KEY at minimum
docker compose -f docker/docker-compose.yml up -d --build
docker compose -f docker/docker-compose.yml logs -f backend celery-worker
```

Services: `postgres`, `redis`, `qdrant`, `backend` (FastAPI, runs `alembic upgrade head` on boot), `celery-worker` (the PDF pipeline), `frontend` (Next.js standalone build). Named volumes `postgres_data`, `qdrant_data`, `backend_storage` persist data across restarts — `backend_storage` is mounted into both `backend` and `celery-worker` so uploaded files are visible to whichever process handles them.

To scale document-processing throughput, scale the worker only:
```bash
docker compose -f docker/docker-compose.yml up -d --scale celery-worker=3
```

## Production considerations (not yet wired — Phase 2 hardening)

- **Secrets**: `SECRET_KEY`, `GEMINI_API_KEY`, and DB credentials should come from a secrets manager, not a committed `.env`. Rotate `SECRET_KEY` invalidates all outstanding JWTs.
- **File storage**: `storage_root` is local disk (mounted volume in Docker). For multi-host deployment, swap `app/services/pdf_processing/storage.py` for S3/GCS/Azure Blob — it's a small, isolated module by design.
- **TLS**: put a reverse proxy (nginx/Caddy/an ALB) in front of both `backend:8000` and `frontend:3000` for HTTPS; the WebSocket progress endpoint needs `Upgrade`/`Connection` headers proxied through.
- **CORS**: `CORS_ORIGINS` in `.env` must list the real frontend origin(s) in production — the default `http://localhost:3000` is dev-only.
- **Rate limiting**: `slowapi` is wired with a single global default (`RATE_LIMIT_DEFAULT`, 60/min per IP) — tune per-route limits for `/documents/upload` and `/chat/.../messages` specifically before opening this up publicly.
- **Migrations**: run `alembic upgrade head` as a release step (the backend container does this automatically on boot; for a rolling deployment, run it once from a one-off task before rolling the new backend image).
- **Model downloads**: BGE-M3 and the BGE reranker download weights from Hugging Face on first use inside the `backend`/`celery-worker` containers — bake them into the image (or a shared volume) for production so cold starts don't hang on a multi-GB download.
- **Observability**: `app/main.py` exposes `/health`; wire it to your orchestrator's liveness probe. Structured logging/tracing is not yet added.
- **Backups**: back up the `postgres_data` volume and the Qdrant collection together — chunk rows and their vectors must stay in sync (a chunk without a vector, or vice versa, breaks retrieval for that document).

## Cloud target (suggested, not implemented)

Managed Postgres (RDS/Cloud SQL) + managed Redis (ElastiCache/Memorystore) + Qdrant Cloud (or self-hosted on a persistent-volume-backed node) + the `backend`/`celery-worker`/`frontend` images on any container platform (ECS, Cloud Run, GKE/EKS). `celery-worker` should run on GPU-backed nodes if you outgrow CPU inference for BGE-M3/BGE-reranker.
