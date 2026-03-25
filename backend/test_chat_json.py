import asyncio
import json
from dotenv import load_dotenv
load_dotenv()
from fastapi import Request
from fastapi import Request
from api.chat import chat, ChatRequest
from services.matcher import load_model
from services.session import get_session
import redis.asyncio as aioredis
import traceback

class MockApp:
    class State:
        redis = None
    state = State()

class MockRequest:
    app = MockApp()

async def main():
    redis_client = aioredis.from_url("redis://localhost:6379", decode_responses=True)
    MockRequest.app.state.redis = redis_client
    
    load_model()
    
    req = ChatRequest(message="Hi, my name is Agastya Toddy. I'd like an appointment for my skin care, specifically acne. Can you tell me which doctor I can go to?")
    
    out = {}
    try:
        resp = await chat(req, MockRequest())
        session = await get_session(redis_client, req.session_id if req.session_id else resp.session_id)
        out["success"] = True
        out["reply"] = resp.reply
        out["tool_calls_executed"] = resp.tool_calls_executed
        out["session_messages"] = session.get("messages", [])
    except Exception as e:
        out["success"] = False
        out["error"] = repr(e)
        out["traceback"] = traceback.format_exc()
        
    with open("test_out.json", "w") as f:
        json.dump(out, f, indent=2)
        
    await redis_client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
