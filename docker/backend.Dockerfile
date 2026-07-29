FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .

RUN mkdir -p /app/storage

EXPOSE 8000

# Default CMD runs the web process AND a Celery worker in the same container,
# sharing this container's local disk — required on single-service platforms
# (Railway without a shared volume across services) where the pipeline's
# uploaded-file storage isn't visible across separate containers. For
# docker-compose, this default is irrelevant: both the `backend` and
# `celery-worker` services override `command:` explicitly and use a shared
# named volume instead, so they still run as properly separate, independently
# scalable processes there. See docs/DEPLOYMENT.md.
CMD ["sh", "-c", "alembic upgrade head && celery -A app.workers.celery_app worker --loglevel=info --pool=solo & exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
