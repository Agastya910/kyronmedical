"""
backend/api/voice_stream.py

Free voice pipeline: Twilio phone call → Deepgram STT → Ollama LLM → edge-tts TTS → Twilio
No OpenAI required. No paid APIs beyond Twilio trial credit.
"""

import asyncio
import audioop
import base64
import io
import json
import os
import logging
from datetime import date
from enum import Enum

import edge_tts
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
from openai import AsyncOpenAI
from pydub import AudioSegment

from services.session import get_session, get_session_by_phone
from services.guardrails import SYSTEM_PROMPT

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory store: Twilio CallSid → session context (set by /api/initiate-call)
_call_context: dict[str, dict] = {}

VOICE_NAME = "en-US-AriaNeural"   # Warm, professional edge-tts voice
TWILIO_CHUNK_BYTES = 160           # 20ms of mulaw audio at 8kHz


class TurnState(Enum):
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"


# ── Audio helpers ──────────────────────────────────────────────────────────────

async def text_to_mulaw_chunks(text: str) -> list[str]:
    """
    Convert text → edge-tts MP3 → PCM 16-bit 8kHz mono → mulaw 8kHz.
    Returns list of base64-encoded 20ms mulaw chunks for Twilio.
    """
    communicate = edge_tts.Communicate(text, VOICE_NAME)
    mp3_buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            mp3_buf.write(chunk["data"])
    mp3_buf.seek(0)

    # pydub: MP3 → PCM 16-bit 8kHz mono
    audio = AudioSegment.from_mp3(mp3_buf)
    audio = audio.set_frame_rate(8000).set_channels(1).set_sample_width(2)
    pcm_bytes = audio.raw_data

    # audioop: PCM 16-bit → mulaw
    mulaw_bytes = audioop.lin2ulaw(pcm_bytes, 2)

    # Split into 20ms chunks
    chunks = []
    for i in range(0, len(mulaw_bytes), TWILIO_CHUNK_BYTES):
        chunk = mulaw_bytes[i : i + TWILIO_CHUNK_BYTES]
        chunks.append(base64.b64encode(chunk).decode())
    return chunks


async def get_llm_voice_response(messages: list[dict]) -> str:
    """Call Ollama with a short max_tokens limit for voice-appropriate replies."""
    client = AsyncOpenAI(
        base_url=os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.environ.get("LLM_API_KEY", "ollama"),
    )
    response = await client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", "hf.co/bartowski/Kimi-K2-Instruct-GGUF:Q4_K_M"),
        messages=messages,
        temperature=0.5,
        max_tokens=80,   # Voice responses must be short — 1 or 2 sentences only
    )
    return (response.choices[0].message.content or "").strip()


# ── TwiML endpoint ─────────────────────────────────────────────────────────────

@router.post("/voice/twiml", response_class=PlainTextResponse)
async def voice_twiml(request: Request):
    """
    Twilio calls this when an outbound call connects.
    We tell Twilio to stream the audio to our WebSocket endpoint.
    """
    form = await request.form()
    call_sid = form.get("CallSid", "")
    to_number = form.get("To", "")

    ctx = _call_context.get(call_sid, {})
    session_id = ctx.get("session_id", "")
    is_reconnect = ctx.get("is_reconnect", False)

    server_base = os.environ.get("SERVER_BASE_URL", "http://localhost:8000")
    ws_base = server_base.replace("https://", "wss://").replace("http://", "ws://")

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{ws_base}/api/voice/stream">
      <Parameter name="session_id" value="{session_id}"/>
      <Parameter name="caller_phone" value="{to_number}"/>
      <Parameter name="is_reconnect" value="{'true' if is_reconnect else 'false'}"/>
    </Stream>
  </Connect>
</Response>"""
    return PlainTextResponse(content=twiml, media_type="application/xml")


# ── Main WebSocket bridge ──────────────────────────────────────────────────────

@router.websocket("/voice/stream")
async def voice_stream(websocket: WebSocket):
    """
    Bidirectional audio bridge:
    Twilio → Deepgram STT → Ollama LLM → edge-tts → Twilio
    """
    await websocket.accept()
    redis = websocket.app.state.redis

    # Mutable state dict (avoids nonlocal complexity across async callbacks)
    state = {
        "turn": TurnState.LISTENING,
        "stream_sid": None,
        "call_messages": [],   # Full conversation for this call (includes system + history)
    }

    transcript_queue: asyncio.Queue[str] = asyncio.Queue()

    # ── Deepgram setup ────────────────────────────────────────────────────
    dg_client = DeepgramClient(os.environ["DEEPGRAM_API_KEY"])
    dg_connection = dg_client.listen.asyncwebsocket.v("1")

    async def on_transcript(self, result, **kwargs):
        try:
            alt = result.channel.alternatives[0]
            text = alt.transcript.strip()
            if text and result.is_final and state["turn"] == TurnState.LISTENING:
                await transcript_queue.put(("transcript", text))
        except Exception as e:
            logger.warning("Transcript parse error: %s", e)

    async def on_utterance_end(self, utterance_end, **kwargs):
        if state["turn"] == TurnState.LISTENING:
            await transcript_queue.put(("utterance_end", ""))

    async def on_error(self, error, **kwargs):
        logger.error("Deepgram error: %s", error)

    dg_connection.on(LiveTranscriptionEvents.Transcript, on_transcript)
    dg_connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)
    dg_connection.on(LiveTranscriptionEvents.Error, on_error)

    dg_options = LiveOptions(
        model="nova-2",
        language="en-US",
        encoding="mulaw",
        sample_rate=8000,
        channels=1,
        smart_format=True,
        endpointing=600,          # 600ms silence → end of utterance
        utterance_end_ms="1200",  # Extra confirmation window
        interim_results=True,
    )

    # ── Send TTS audio to caller ──────────────────────────────────────────
    async def speak(text: str):
        if not text:
            return
        state["turn"] = TurnState.SPEAKING
        logger.info("Speaking: %s", text[:60])
        try:
            chunks = await text_to_mulaw_chunks(text)
            for chunk_b64 in chunks:
                await websocket.send_text(json.dumps({
                    "event": "media",
                    "streamSid": state["stream_sid"],
                    "media": {"payload": chunk_b64},
                }))
                await asyncio.sleep(0.019)  # Slightly under 20ms to avoid buffer underrun
            # Mark playback end so we know when to start listening again
            await websocket.send_text(json.dumps({
                "event": "mark",
                "streamSid": state["stream_sid"],
                "mark": {"name": "tts_done"},
            }))
        except Exception as e:
            logger.error("TTS error: %s", e)
        finally:
            state["turn"] = TurnState.LISTENING

    # ── Transcript processor loop ─────────────────────────────────────────
    async def process_loop():
        accumulated: list[str] = []
        while True:
            event_type, text = await transcript_queue.get()

            if event_type == "stop":
                break

            if event_type == "transcript":
                accumulated.append(text)

            elif event_type == "utterance_end":
                if not accumulated:
                    continue
                full_text = " ".join(accumulated).strip()
                accumulated.clear()
                if not full_text:
                    continue

                logger.info("User: %s", full_text)
                state["turn"] = TurnState.PROCESSING

                state["call_messages"].append({"role": "user", "content": full_text})
                try:
                    reply = await get_llm_voice_response(state["call_messages"])
                    state["call_messages"].append({"role": "assistant", "content": reply})
                    logger.info("AI: %s", reply)
                    await speak(reply)
                except Exception as e:
                    logger.error("LLM error: %s", e)
                    state["turn"] = TurnState.LISTENING

    try:
        # Start Deepgram
        if not await dg_connection.start(dg_options):
            logger.error("Deepgram failed to connect")
            return

        processor = asyncio.create_task(process_loop())

        # ── Receive Twilio WebSocket messages ─────────────────────────────
        async for raw in websocket.iter_text():
            msg = json.loads(raw)
            event = msg.get("event")

            if event == "start":
                state["stream_sid"] = msg["start"]["streamSid"]
                params = msg["start"].get("customParameters", {})
                session_id = params.get("session_id", "")
                caller_phone = params.get("caller_phone", "")
                is_reconnect = params.get("is_reconnect", "false") == "true"

                # Load Redis session
                if session_id:
                    session_data = await get_session(redis, session_id)
                elif caller_phone:
                    sid = await get_session_by_phone(redis, caller_phone)
                    session_data = await get_session(redis, sid) if sid else {}
                else:
                    session_data = {}

                belief = session_data.get("belief_state", {})
                prior_messages = session_data.get("messages", [])
                first_name = belief.get("first_name", "")

                # Build system prompt for voice call
                system_prompt = (
                    SYSTEM_PROMPT.format(
                        current_date=date.today().strftime("%B %d, %Y"),
                        belief_state=json.dumps(belief, indent=2) if belief else "No prior data.",
                    )
                    + "\n\n━━ VOICE RULES ━━\n"
                    + "Keep every single response to ONE or TWO short sentences maximum. "
                    + "Spell all numbers and dates in words. "
                    + "No markdown, no lists, no bullet points. "
                    + "Never provide medical advice. "
                    + "Be warm and natural like a receptionist on the phone."
                )

                # Initialize call_messages with system + prior context
                state["call_messages"] = [{"role": "system", "content": system_prompt}]
                for m in prior_messages[-8:]:
                    if m.get("role") in ("user", "assistant") and m.get("content"):
                        state["call_messages"].append({"role": m["role"], "content": m["content"]})

                # Build greeting
                booked = belief.get("booked_appointment")
                if is_reconnect and booked:
                    doc = booked.get("doctor", {})
                    slot = booked.get("slot", {})
                    greeting = (
                        f"Welcome back{', ' + first_name if first_name else ''}! "
                        f"Your appointment with {doc.get('name', 'your doctor')} is confirmed. How can I help you?"
                    )
                elif is_reconnect:
                    greeting = (
                        f"Welcome back{', ' + first_name if first_name else ''}! "
                        f"I remember we were scheduling your appointment. Let me pick up right where we left off."
                    )
                elif first_name:
                    greeting = (
                        f"Hi {first_name}, this is Kyron Care calling. "
                        f"I'm here to continue scheduling your appointment from our web chat. Can you hear me okay?"
                    )
                else:
                    greeting = (
                        "Hi, this is Kyron Care. "
                        "I'm here to help you schedule your appointment. Can you hear me okay?"
                    )

                asyncio.create_task(speak(greeting))

            elif event == "media":
                # Only forward audio to Deepgram when we're listening (not while AI is speaking)
                if state["turn"] == TurnState.LISTENING:
                    audio_bytes = base64.b64decode(msg["media"]["payload"])
                    await dg_connection.send(audio_bytes)

            elif event == "mark":
                pass  # Playback acknowledged

            elif event == "stop":
                logger.info("Twilio stream stopped")
                break

        await transcript_queue.put(("stop", ""))
        await processor

    except WebSocketDisconnect:
        logger.info("Twilio WebSocket disconnected cleanly")
    except Exception as e:
        logger.error("Voice stream fatal error: %s", e, exc_info=True)
    finally:
        try:
            await dg_connection.finish()
        except Exception:
            pass
