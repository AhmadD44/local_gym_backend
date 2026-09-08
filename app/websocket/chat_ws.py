"""Chat WebSocket endpoint with Redis pub/sub fan-out so messages reach
connected clients regardless of which FastAPI instance they're attached to
(required for horizontal scaling — connections are process-local, but the
Redis channel is shared).

Auth: the access token is passed as a query parameter (`?token=...`)
because browser/Flutter WebSocket clients cannot always set an
Authorization header on the initial handshake. The token is validated
exactly like the REST access token (same signature/claims checks).
"""

import asyncio
import logging
import uuid
from collections import defaultdict

import orjson
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis
from app.core.security import TokenError, TokenType, decode_token
from app.models.user import User
from app.schemas.chat import MessageRead
from app.services import chat_service

logger = logging.getLogger("gym.ws")
router = APIRouter(prefix="/ws", tags=["websocket"])

_CHANNEL_PREFIX = "chat:conversation:"
_MAX_MESSAGES_PER_MINUTE = 30


class ConnectionManager:
    def __init__(self):
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self._listener_tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def connect(self, conversation_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._rooms[conversation_id].add(websocket)
            if conversation_id not in self._listener_tasks:
                self._listener_tasks[conversation_id] = asyncio.create_task(self._listen(conversation_id))

    async def disconnect(self, conversation_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(conversation_id)
            if room and websocket in room:
                room.remove(websocket)
            if room is not None and not room:
                self._rooms.pop(conversation_id, None)
                task = self._listener_tasks.pop(conversation_id, None)
                if task:
                    task.cancel()

    async def _listen(self, conversation_id: str) -> None:
        redis = get_redis()
        pubsub = redis.pubsub()
        channel = f"{_CHANNEL_PREFIX}{conversation_id}"
        await pubsub.subscribe(channel)
        try:
            async for raw in pubsub.listen():
                if raw["type"] != "message":
                    continue
                room = self._rooms.get(conversation_id, set())
                stale = []
                for ws in room:
                    try:
                        await ws.send_text(raw["data"])
                    except Exception:
                        stale.append(ws)
                for ws in stale:
                    room.discard(ws)
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()


manager = ConnectionManager()


async def publish_message(conversation_id: uuid.UUID, message: MessageRead) -> None:
    redis = get_redis()
    channel = f"{_CHANNEL_PREFIX}{conversation_id}"
    await redis.publish(channel, orjson.dumps(message.model_dump(mode="json")).decode())


async def _authenticate_ws(websocket: WebSocket) -> User | None:
    token = websocket.query_params.get("token")
    if not token:
        return None
    try:
        payload = decode_token(token, expected_type=TokenType.ACCESS)
    except TokenError:
        return None

    async with AsyncSessionLocal() as db:
        try:
            user = await db.get(User, uuid.UUID(payload["sub"]))
        except (KeyError, ValueError):
            return None
        if user is None or not user.is_active:
            return None
        return user


@router.websocket("/chat/{conversation_id}")
async def chat_websocket(websocket: WebSocket, conversation_id: uuid.UUID):
    user = await _authenticate_ws(websocket)
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    async with AsyncSessionLocal() as db:
        try:
            await chat_service.assert_participant(db, conversation_id=conversation_id, user_id=user.id)
        except Exception:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    room_key = str(conversation_id)
    await manager.connect(room_key, websocket)
    redis = get_redis()
    rate_key = f"ws_rate:{user.id}"

    try:
        while True:
            raw = await websocket.receive_text()

            count = await redis.incr(rate_key)
            if count == 1:
                await redis.expire(rate_key, 60)
            if count > _MAX_MESSAGES_PER_MINUTE:
                await websocket.send_text(orjson.dumps({"error": "rate_limited"}).decode())
                continue

            try:
                payload = orjson.loads(raw)
                content = str(payload.get("content", "")).strip()
            except orjson.JSONDecodeError:
                content = raw.strip()

            if not content or len(content) > 4000:
                continue

            async with AsyncSessionLocal() as db:
                message = await chat_service.post_message(
                    db, conversation_id=conversation_id, sender_id=user.id, content=content
                )
                await publish_message(conversation_id, MessageRead.model_validate(message))
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(room_key, websocket)
