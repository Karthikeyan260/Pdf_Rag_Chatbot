import httpx
import pytest
import redis as redis_sync
from sqlalchemy import text

from app.core.config import get_settings
from app.db.base import Base
from app.db.sync_session import sync_engine
from app.main import app

settings = get_settings()


def _infra_reachable() -> bool:
    try:
        with sync_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        redis_sync.Redis.from_url(settings.redis_url).ping()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session", autouse=True)
def _require_infra():
    if not _infra_reachable():
        pytest.skip(
            "Postgres/Redis are not reachable — run "
            "`docker compose -f docker/docker-compose.yml up -d postgres redis qdrant` "
            "before running integration tests."
        )


@pytest.fixture(scope="session", autouse=True)
def _schema(_require_infra):
    Base.metadata.create_all(bind=sync_engine)
    yield
    Base.metadata.drop_all(bind=sync_engine)


@pytest.fixture(autouse=True)
def _clean_tables(_schema):
    yield
    with sync_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
