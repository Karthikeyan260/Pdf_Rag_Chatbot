import json

import redis.asyncio as aioredis

from app.core.config import get_settings

settings = get_settings()


def progress_channel(document_id: str) -> str:
    return f"document:{document_id}:progress"


async def publish_progress(document_id: str, status: str, percent: int, detail: str = "") -> None:
    client = aioredis.from_url(settings.redis_url)
    try:
        payload = json.dumps({"document_id": document_id, "status": status, "percent": percent, "detail": detail})
        await client.publish(progress_channel(document_id), payload)
    finally:
        await client.aclose()
