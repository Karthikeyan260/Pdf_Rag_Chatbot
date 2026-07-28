from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Celery tasks run their own event loop per task (see workers/tasks.py); reusing the
# FastAPI async engine's connection pool across those loops breaks asyncpg. The
# background pipeline therefore uses a plain synchronous engine/session instead.
sync_database_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
sync_engine = create_engine(sync_database_url, pool_pre_ping=True)
SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False, class_=Session)
