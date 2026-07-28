# Deployment Guide

## Vercel (frontend) + Railway (backend/worker/Postgres/Redis) — recommended split

This is the fastest path to a live URL without managing servers. You need accounts on both platforms (free tiers work for a demo) — I can't create these accounts or click through their dashboards for you, so this is a runbook to follow yourself; ping me if any step errors and I'll debug the config.

### 1. Railway — backend, worker, Postgres, Redis

1. **New Project → Deploy from GitHub repo** → pick `Karthikeyan260/Pdf_Rag_Chatbot`. Railway will find `railway.json` at the repo root and build `docker/backend.Dockerfile` automatically — this is your **backend (web)** service.
2. **Add Postgres**: in the same project, `+ New → Database → Add PostgreSQL`. Open its **Variables** tab and copy the individual `PGHOST`/`PGPORT`/`PGUSER`/`PGPASSWORD`/`PGDATABASE` values (not the ready-made `DATABASE_URL` — Railway's default uses the plain `postgresql://` scheme, but this app's async engine needs the `postgresql+asyncpg://` driver).
3. **Add Redis**: `+ New → Database → Add Redis`. Copy its connection string (looks like `redis://default:<password>@<host>:<port>`).
4. On the **backend service → Variables**, add:
   ```
   SECRET_KEY=<generate a random 64-char string>
   GEMINI_API_KEY=<your key>
   DATABASE_URL=postgresql+asyncpg://<PGUSER>:<PGPASSWORD>@<PGHOST>:<PGPORT>/<PGDATABASE>
   REDIS_URL=<redis connection string>/0
   CELERY_BROKER_URL=<redis connection string>/1
   CELERY_RESULT_BACKEND=<redis connection string>/2
   QDRANT_URL=<see step 5>
   QDRANT_API_KEY=<see step 5>
   CORS_ORIGINS=["https://<your-vercel-app>.vercel.app"]
   ```
   (Railway auto-injects `PORT`; the Dockerfile's CMD already binds to it.)
5. **Vector store — Qdrant Cloud**: Railway has no native Qdrant plugin. Create a free cluster at [cloud.qdrant.io](https://cloud.qdrant.io), copy its URL and API key into `QDRANT_URL`/`QDRANT_API_KEY` above. (Alternative: `+ New → Empty Service → Deploy from Docker Image` with image `qdrant/qdrant:v1.12.4` and a mounted volume, self-hosted on Railway instead.)
6. **Add the worker**: `+ New → GitHub Repo` again, same repo. In this second service's **Settings → Deploy**, set **Custom Start Command** to:
   ```
   celery -A app.workers.celery_app worker --loglevel=info --pool=solo
   ```
   Copy the *same* environment variables from step 4 onto this service too (backend and worker both need DB/Redis/Qdrant access; the worker does not need `CORS_ORIGINS`).
7. Deploy. Check the backend service's public URL + `/health`, and `/docs` for the Swagger UI. Watch the worker's logs when you upload a test document.

### 2. Vercel — frontend

1. **Add New Project → Import** the same GitHub repo.
2. **Root Directory**: set to `frontend` (Vercel's monorepo picker, at import time or in Project Settings → General).
3. Vercel auto-detects Next.js; `frontend/vercel.json` already forces `npm install --legacy-peer-deps` (needed since `react-pdf`/`pdfjs-dist` haven't published official React 19 peer ranges yet).
4. **Environment Variables**: add `NEXT_PUBLIC_API_URL=https://<your-railway-backend-domain>` (the backend service's public URL from step 1.1/1.7 — no trailing slash).
5. Deploy. Once you have the Vercel URL, go back to Railway and set the backend's `CORS_ORIGINS` to include it (step 1.4), then redeploy the backend.

### Post-deploy checklist

- Sign up on the live frontend URL, confirm `/auth/me` works (network tab should show calls to your Railway URL, not `localhost`).
- Upload `sample_pdfs/demo_annual_report.pdf`, confirm the worker logs show it moving through `queued → extracting → chunking → embedding → done`.
- Ask "What was the net profit in 2024?" and confirm a streamed, cited answer.
- The first embedding/rerank call downloads BGE-M3 + BGE-reranker weights (a few GB) — the worker's first document will be slow; consider Railway's persistent volume for the model cache dir (`~/.cache/huggingface`) if this happens on every worker restart.

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
