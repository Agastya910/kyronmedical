"""
Redis session store for conversation persistence across web ↔ phone.
"""
import json
import redis.asyncio as aioredis
from datetime import timedelta
from typing import Optional

SESSION_TTL = int(timedelta(hours=24).total_seconds())
_pool: Optional[aioredis.Redis] = None


async def get_redis(redis_url: str) -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(redis_url, decode_responses=True)
    return _pool


async def get_session(redis: aioredis.Redis, session_id: str) -> dict:
    raw = await redis.get(f"session:{session_id}")
    if raw:
        return json.loads(raw)
    return {"messages": [], "belief_state": {}, "booked_appointment": None}


async def save_session(redis: aioredis.Redis, session_id: str, data: dict):
    await redis.setex(
        f"session:{session_id}",
        SESSION_TTL,
        json.dumps(data, default=str),
    )


async def register_phone(redis: aioredis.Redis, phone: str, session_id: str):
    """Maps phone number → session_id for reconnect-on-callback."""
    await redis.setex(f"phone:{phone}", SESSION_TTL, session_id)


async def get_session_by_phone(redis: aioredis.Redis, phone: str) -> Optional[str]:
    return await redis.get(f"phone:{phone}")
