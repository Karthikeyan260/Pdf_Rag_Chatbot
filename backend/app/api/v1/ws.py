import asyncio
import json

import redis.asyncio as aioredis
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.security import decode_token
from app.services.pdf_processing.progress import progress_channel

router = APIRouter(tags=["ws"])
settings = get_settings()


@router.websocket("/ws/documents/{document_id}/progress")
async def document_progress(websocket: WebSocket, document_id: str, token: str = Query(...)) -> None:
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=4401)
        return

    await websocket.accept()
    client = aioredis.from_url(settings.redis_url)
    pubsub = client.pubsub()
    await pubsub.subscribe(progress_channel(document_id))

    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                raw = message["data"]
                text = raw.decode() if isinstance(raw, bytes) else raw
                await websocket.send_text(text)
                if json.loads(text).get("status") in ("done", "failed"):
                    break
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(progress_channel(document_id))
        await pubsub.aclose()
        await client.aclose()
        try:
            await websocket.close()
        except RuntimeError:
            pass
