"""
Kyron Medical — FastAPI Backend Entry Point
"""
import logging
import os
import sys

import redis.asyncio as aioredis
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure local packages are importable
sys.path.insert(0, os.path.dirname(__file__))

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

from api.chat import router as chat_router
from api.call import router as call_router
from api.webhook import router as webhook_router
from api.voice_stream import router as voice_router
from services.matcher import load_model
from services.db import init_db, get_availability, save_availability


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Kyron Medical API…")
    load_model()  # Load BGE-M3 and pre-embed doctors
    app.state.redis = aioredis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379"),
        decode_responses=True,
    )
    logger.info("Redis connected.")
    logger.info("Initializing SQLite database...")
    await init_db()
    
    # Seed availability if missing
    import json
    from data.doctors import AVAILABILITY
    avail_data = await get_availability()
    if not avail_data:
        await save_availability(AVAILABILITY)
        logger.info("Seeded default availability to SQLite.")
        
    yield
    # Shutdown
    await app.state.redis.aclose()
    logger.info("Redis closed.")


app = FastAPI(
    title="Kyron Medical API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the Next.js frontend
frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "https://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(chat_router, prefix="/api")
app.include_router(call_router, prefix="/api")
app.include_router(webhook_router, prefix="/api")
app.include_router(voice_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "kyron-medical-api"}

@app.post("/api/reset")
async def reset_database(request: Request):
    """Testing utility completely resets the Redis mock database and calendar back to clean defaults."""
    redis = request.app.state.redis
    import json
    import aiosqlite
    from data.doctors import AVAILABILITY
    from services.db import DB_PATH
    
    # Target all session keys
    keys = await redis.keys("kyron:*")
    if keys:
        await redis.delete(*keys)
        
    session_keys = await redis.keys("session:*")
    if session_keys:
        await redis.delete(*session_keys)
        
    phone_keys = await redis.keys("phone:*")
    if phone_keys:
        await redis.delete(*phone_keys)
        
    # Reset SQLite
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM patients')
        await db.execute('DELETE FROM kv_store')
        await db.commit()
        
    # Immediately seed fresh calendar
    await save_availability(AVAILABILITY)
    
    return {
        "success": True, 
        "message": f"Successfully flushed {len(keys)} records and reset doctor availability to default state."
    }
