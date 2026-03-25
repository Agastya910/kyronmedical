"""
backend/api/webhook.py

POST /api/webhook/twilio  — Handles inbound Twilio voice calls.
When a patient calls back, looks up their prior session and reconnects context.
"""

import os
import logging
import redis.asyncio as aioredis
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from services.session import get_session, get_session_by_phone
from api.voice_stream import _call_context

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhook/twilio", response_class=PlainTextResponse)
async def twilio_inbound_webhook(request: Request):
    """
    Twilio calls this when a patient dials our phone number directly.
    We look up their number in Redis to find any prior session.
    """
    redis: aioredis.Redis = request.app.state.redis
    form = await request.form()
    call_sid = form.get("CallSid", "")
    caller_phone = form.get("From", "")

    is_reconnect = False
    session_id = ""

    if caller_phone:
        session_id = await get_session_by_phone(redis, caller_phone) or ""
        if session_id:
            is_reconnect = True
            logger.info("Returning caller %s matched to session %s", caller_phone, session_id)

    _call_context[call_sid] = {
        "session_id": session_id,
        "is_reconnect": is_reconnect,
    }

    server_base = os.environ.get("SERVER_BASE_URL", "http://localhost:8000")
    ws_base = server_base.replace("https://", "wss://").replace("http://", "ws://")

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{ws_base}/api/voice/stream">
      <Parameter name="session_id" value="{session_id}"/>
      <Parameter name="caller_phone" value="{caller_phone}"/>
      <Parameter name="is_reconnect" value="{'true' if is_reconnect else 'false'}"/>
    </Stream>
  </Connect>
</Response>"""

    return PlainTextResponse(content=twiml, media_type="application/xml")
