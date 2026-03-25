"""
backend/api/call.py

POST /api/initiate-call  — Uses Twilio to place an outbound call to the patient.
The call connects to /api/voice/twiml which bridges to OpenAI Realtime.
"""

import os
import logging
import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from twilio.rest import Client as TwilioClient

from services.session import get_session, register_phone
from api.voice_stream import _call_context

logger = logging.getLogger(__name__)
router = APIRouter()


class InitiateCallRequest(BaseModel):
    phone_number: str
    session_id: str


@router.post("/initiate-call")
async def initiate_call(body: InitiateCallRequest, request: Request):
    redis: aioredis.Redis = request.app.state.redis

    # Verify session exists
    session_data = await get_session(redis, body.session_id)
    belief = session_data.get("belief_state", {})

    # Register phone->session mapping for reconnect-on-callback
    if body.phone_number:
        await register_phone(redis, body.phone_number, body.session_id)

    server_base = os.environ.get("SERVER_BASE_URL", "http://localhost:8000")
    twiml_url = f"{server_base}/api/voice/twiml"

    try:
        client = TwilioClient(
            os.environ["TWILIO_ACCOUNT_SID"],
            os.environ["TWILIO_AUTH_TOKEN"],
        )

        call = client.calls.create(
            to=body.phone_number,
            from_=os.environ["TWILIO_PHONE_NUMBER"],
            url=twiml_url,
            method="POST",
            send_digits="ww1",
        )

        # Store context so the TwiML webhook can look it up by CallSid
        _call_context[call.sid] = {
            "session_id": body.session_id,
            "is_reconnect": False,
            "belief": belief,
        }

        logger.info("Outbound call placed: sid=%s to=%s", call.sid, body.phone_number)
        return {"success": True, "call_sid": call.sid}

    except Exception as e:
        logger.error("Twilio call error: %s", e)
        raise HTTPException(status_code=502, detail=f"Could not place call: {str(e)}")
