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

# Default CMD is the web process (migrates then serves) and honors $PORT for
# platforms that assign it dynamically (Railway/Render). The Celery worker is
# deployed from this same image with its start command overridden to
# `celery -A app.workers.celery_app worker --loglevel=info --pool=solo` —
# see docs/DEPLOYMENT.md.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
