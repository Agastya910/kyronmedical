from dotenv import load_dotenv
load_dotenv()
import asyncio
import json
from fastapi import Request
from api.chat import chat, ChatRequest

class MockApp:
    class State:
        redis = None
    state = State()

class MockRequest:
    app = MockApp()

import redis.asyncio as aioredis

async def main():
    redis_client = aioredis.from_url("redis://localhost:6379", decode_responses=True)
    MockRequest.app.state.redis = redis_client
    from services.matcher import load_model
    load_model()
    
    req = ChatRequest(message="I am Agastya Toddy. My date of birth is 4 April 2000, and my phone number is 8482-123-456. Email address is agastyasample@gmail.com. I have an appointment for my skin care, specifically acne. Can you tell me which doctor I can go to?")
    print("Calling chat endpoint...")
    try:
        resp = await chat(req, MockRequest())
        print("Success!")
        print("Reply:", resp.reply)
        print("Tool calls:", resp.tool_calls_executed)
    except Exception as e:
        print("Error:", repr(e))
        import traceback
        traceback.print_exc()
    
    await redis_client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
