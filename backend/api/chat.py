"""
/api/chat  — Main chat endpoint with Kimi K2.5 (via Ollama) + function calling.
"""
import json
import os
import uuid
from datetime import date
from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from data.doctors import AVAILABILITY, DOCTORS_BY_ID, PRACTICE_INFO
from services.guardrails import SYSTEM_PROMPT, sanitize_input, validate_output
from services.matcher import match_doctor
from services.session import get_redis, get_session, save_session, register_phone
from services.notifications import send_confirmation_email, send_confirmation_sms

router = APIRouter()

# ── Tool definitions ──────────────────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "match_doctor_to_complaint",
            "description": "Match the patient's complaint to the right doctor.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chief_complaint": {"type": "string"}
                },
                "required": ["chief_complaint"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_slots",
            "description": "Get available appointment slots for a doctor.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_id": {"type": "string"},
                    "day_of_week": {"type": "string", "enum": ["Monday","Tuesday","Wednesday","Thursday","Friday"]},
                    "limit": {"type": "integer", "default": 3},
                },
                "required": ["doctor_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Book a confirmed appointment slot.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_id": {"type": "string"},
                    "slot_id": {"type": "string"},
                    "patient_info": {
                        "type": "object",
                        "properties": {
                            "first_name": {"type": "string"},
                            "last_name": {"type": "string"},
                            "dob": {"type": "string"},
                            "phone": {"type": "string"},
                            "email": {"type": "string"},
                        },
                        "required": ["first_name","last_name","dob","phone","email"],
                    },
                    "sms_opt_in": {"type": "boolean", "default": False},
                },
                "required": ["doctor_id","slot_id","patient_info"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_practice_info",
            "description": "Get practice address, phone, and hours.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_belief_state",
            "description": "Save newly collected patient data fields.",
            "parameters": {
                "type": "object",
                "properties": {"updates": {"type": "object"}},
                "required": ["updates"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_patient_history",
            "description": "Check if a returning patient exists by name or phone. Returns only found/not-found — no PII.",
            "parameters": {
                "type": "object",
                "properties": {
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                    "phone": {"type": "string"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "verify_patient_id",
            "description": "Verify the spoken Patient ID to unlock the patient profile.",
            "parameters": {
                "type": "object",
                "properties": {"patient_id": {"type": "string"}},
                "required": ["patient_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_patient_id_reminder",
            "description": "Send the patient's forgotten ID via SMS/email.",
            "parameters": {
                "type": "object",
                "properties": {"phone": {"type": "string"}},
                "required": ["phone"]
            }
        }
    },
]


# ── Tool execution ─────────────────────────────────────────────────────────────
async def execute_tool(name: str, args: dict, session_data: dict, redis_client: aioredis.Redis) -> tuple[str, dict]:
    """Execute a tool call and return (result_json, updated_session_data)."""
    belief = session_data.get("belief_state", {})

    if name == "match_doctor_to_complaint":
        # ── GATE: All 5 patient fields must be collected before matching ──
        required = ["first_name", "last_name", "dob", "phone", "email"]
        missing = [f for f in required if not belief.get(f)]
        if missing:
            return json.dumps({
                "error": "BLOCKED. Patient intake is incomplete.",
                "missing_fields": missing,
                "instruction": f"You MUST collect these fields from the patient BEFORE matching a doctor: {', '.join(missing)}. Ask the patient for each missing field, call update_belief_state to save them, then try again."
            }), session_data

        complaint = args.get("chief_complaint")
        if not complaint:
            return json.dumps({"error": "Missing required argument 'chief_complaint'"}), session_data
            
        result = match_doctor(complaint)
        if result["matched"]:
            belief["matched_doctor_id"] = result["doctor"]["id"]
            belief["matched_doctor_name"] = result["doctor"]["name"]
        session_data["belief_state"] = belief
        return json.dumps(result), session_data

    elif name == "get_available_slots":
        doctor_id = args.get("doctor_id")
        if not doctor_id:
            return json.dumps({"error": "Missing required argument 'doctor_id'"}), session_data
            
        avail_str = await redis_client.get("kyron:availability")
        avail_data = json.loads(avail_str) if avail_str else AVAILABILITY
        slots = avail_data.get(doctor_id, [])
        
        day_filter = args.get("day_of_week")
        if day_filter:
            slots = [s for s in slots if s["day_of_week"] == day_filter]
        available = [s for s in slots if s["available"]]
        limit = args.get("limit", 3)
        return json.dumps({"slots": available[:limit], "doctor": DOCTORS_BY_ID.get(doctor_id)}), session_data

    elif name == "book_appointment":
        # ── GATE: All 5 patient fields must be in belief state before booking ──
        required = ["first_name", "last_name", "dob", "phone", "email"]
        missing = [f for f in required if not belief.get(f)]
        if missing:
            return json.dumps({
                "error": "BLOCKED. Cannot book without complete patient information.",
                "missing_fields": missing,
                "instruction": f"You MUST collect these fields first: {', '.join(missing)}. Ask the patient, call update_belief_state, then retry booking."
            }), session_data

        doctor_id = args.get("doctor_id")
        slot_id = args.get("slot_id")
        patient = args.get("patient_info", {})
        
        if not doctor_id or not slot_id or not patient:
            return json.dumps({"error": "Missing required arguments ('doctor_id', 'slot_id', 'patient_info')"}), session_data
            
        sms_opt_in = args.get("sms_opt_in", False)

        avail_str = await redis_client.get("kyron:availability")
        avail_data = json.loads(avail_str) if avail_str else AVAILABILITY

        # Find and mark slot unavailable
        target_slot = None
        for s in avail_data.get(doctor_id, []):
            if s["slot_id"] == slot_id and s["available"]:
                s["available"] = False
                target_slot = s
                break

        if not target_slot:
            return json.dumps({"success": False, "error": "Slot no longer available"}), session_data

        doctor = DOCTORS_BY_ID[doctor_id]

        # Store booking in belief state
        patient_id = patient.get("patient_id") or "KMG-" + str(uuid.uuid4())[:6].upper()
        patient["patient_id"] = patient_id

        booking = {
            "doctor": doctor,
            "slot": target_slot,
            "patient": patient,
            "sms_opt_in": sms_opt_in,
        }
        belief.update({
            "patient_id": patient_id,
            "first_name": patient.get("first_name", ""),
            "last_name": patient.get("last_name", ""),
            "dob": patient.get("dob", ""),
            "phone": patient.get("phone", ""),
            "email": patient.get("email", ""),
            "booked_appointment": booking,
        })
        session_data["belief_state"] = belief
        session_data["booked_appointment"] = booking
        
        # Save back to Redis
        await redis_client.set("kyron:availability", json.dumps(avail_data))
        
        # Save patient to Redis!
        patient_key = f"kyron:patient_profile:{patient.get('first_name', '').lower().strip()}_{patient.get('last_name', '').lower().strip()}"
        await redis_client.set(patient_key, json.dumps(patient))
        phone_key = f"kyron:patient_profile:{patient.get('phone', '').strip()}"
        await redis_client.set(phone_key, json.dumps(patient))

        # Store for frontend appointment card rendering
        session_data["pending_notifications"] = {
            "patient": patient,
            "doctor": doctor,
            "slot": target_slot,
            "sms_opt_in": sms_opt_in,
        }

        return json.dumps({
            "success": True,
            "booking": {
                "doctor_name": doctor["name"],
                "specialty": doctor["specialty"],
                "date": target_slot["display_date"],
                "time": target_slot["time"],
                "patient_email": patient.get("email", ""),
            },
        }), session_data

    elif name == "get_practice_info":
        return json.dumps(PRACTICE_INFO), session_data

    elif name == "search_patient_history":
        fname = args.get("first_name", "")
        lname = args.get("last_name", "")
        phone = args.get("phone", "")
        
        history = None
        if phone:
            history_str = await redis_client.get(f"kyron:patient_profile:{phone.strip()}")
            if history_str:
                history = json.loads(history_str)
        if not history and fname and lname:
            history_str = await redis_client.get(f"kyron:patient_profile:{fname.lower().strip()}_{lname.lower().strip()}")
            if history_str:
                history = json.loads(history_str)
                
        if history:
            # Store the profile in a HIDDEN session field — the LLM never sees this data
            session_data["_pending_verification"] = history
            return json.dumps({
                "found": True, 
                "message": "A matching account was found. You MUST now ask the user for their Patient ID (format: KMG-XXXXXX) to verify their identity. Do NOT reveal any personal details. If they forgot their ID, ask for their phone number and call send_patient_id_reminder."
            }), session_data
        else:
            return json.dumps({"found": False, "note": "No previous records found for this patient. Treat them as a new patient."}), session_data

    elif name == "verify_patient_id":
        user_pid = args.get("patient_id", "").strip().upper()
        pending = session_data.get("_pending_verification")
        
        if not pending:
            return json.dumps({"verified": False, "error": "No pending profile to verify. Call search_patient_history first."}), session_data
        
        real_pid = pending.get("patient_id", "").strip().upper()
        
        if user_pid == real_pid:
            # Verification passed! Now unlock the profile into the belief state
            belief.update({
                "patient_id": pending.get("patient_id"),
                "first_name": pending.get("first_name", ""),
                "last_name": pending.get("last_name", ""),
                "dob": pending.get("dob", ""),
                "phone": pending.get("phone", ""),
                "email": pending.get("email", ""),
                "identity_verified": True,
            })
            session_data["belief_state"] = belief
            del session_data["_pending_verification"]
            return json.dumps({
                "verified": True,
                "patient_data": pending,
                "message": "Identity verified! You may now confirm the patient's details and proceed with scheduling."
            }), session_data
        else:
            return json.dumps({
                "verified": False,
                "message": "The Patient ID does not match. Ask the user to try again or offer to send a reminder via send_patient_id_reminder."
            }), session_data

    elif name == "send_patient_id_reminder":
        phone = args.get("phone", "")
        if not phone:
            return json.dumps({"error": "Missing phone number."}), session_data
        
        history_str = await redis_client.get(f"kyron:patient_profile:{phone.strip()}")
        if history_str:
            history = json.loads(history_str)
            pid = history.get("patient_id")
            if pid:
                from services.notifications import send_id_reminder_sms, send_id_reminder_email
                await send_id_reminder_sms(history)
                if history.get("email"):
                    await send_id_reminder_email(history)
                return json.dumps({"success": True, "message": "A reminder with the Patient ID was sent to the patient's phone and email. Ask the user to check their messages and then provide their Patient ID."}), session_data
                
        return json.dumps({"error": "No matching patient profile found for this phone number."}), session_data

    elif name == "update_belief_state":
        updates = args.get("updates", {})
        belief.update(updates)
        session_data["belief_state"] = belief
        
        # If we now have contact info, save/update the profile early
        if belief.get("first_name") and belief.get("last_name") and belief.get("phone"):
            p_dict = {
                "patient_id": belief.get("patient_id") or "KMG-" + str(uuid.uuid4())[:6].upper(),
                "first_name": belief.get("first_name"),
                "last_name": belief.get("last_name"),
                "dob": belief.get("dob"),
                "phone": belief.get("phone"),
                "email": belief.get("email"),
            }
            belief["patient_id"] = p_dict["patient_id"]
            session_data["belief_state"] = belief
            await redis_client.set(f"kyron:patient_profile:{p_dict['first_name'].lower().strip()}_{p_dict['last_name'].lower().strip()}", json.dumps(p_dict))
            await redis_client.set(f"kyron:patient_profile:{p_dict['phone'].strip()}", json.dumps(p_dict))
            
        return json.dumps({"updated": True, "note": "Belief state updated."}), session_data

    return json.dumps({"error": "Unknown tool"}), session_data


# ── Deterministic Intake Endpoints (zero LLM calls) ───────────────────────────

class PatientIntakeRequest(BaseModel):
    first_name: str
    last_name: str
    dob: str
    phone: str
    email: str

class PatientIntakeResponse(BaseModel):
    patient_id: str
    session_id: str
    belief_state: dict

@router.post("/patient-intake", response_model=PatientIntakeResponse)
async def patient_intake(body: PatientIntakeRequest, request: Request):
    """Deterministic new-patient registration. Zero LLM calls."""
    redis: aioredis.Redis = request.app.state.redis
    session_id = str(uuid.uuid4())
    
    # Generate patient ID
    patient_id = "KMG-" + str(uuid.uuid4())[:6].upper()
    
    # Build profile
    profile = {
        "patient_id": patient_id,
        "first_name": body.first_name,
        "last_name": body.last_name,
        "dob": body.dob,
        "phone": body.phone,
        "email": body.email,
    }
    
    # Save to Redis under phone key (primary) and name key (secondary)
    await redis.set(
        f"kyron:patient_profile:{body.phone.strip()}",
        json.dumps(profile),
    )
    name_key = f"{body.first_name.strip().lower()}_{body.last_name.strip().lower()}"
    await redis.set(
        f"kyron:patient_profile:{name_key}",
        json.dumps(profile),
    )
    
    # Pre-fill the session belief state so the LLM skips intake entirely
    belief = {
        "patient_id": patient_id,
        "first_name": body.first_name,
        "last_name": body.last_name,
        "dob": body.dob,
        "phone": body.phone,
        "email": body.email,
    }
    session_data = {
        "messages": [],
        "belief_state": belief,
    }
    await save_session(redis, session_id, session_data)
    
    return PatientIntakeResponse(
        patient_id=patient_id,
        session_id=session_id,
        belief_state=belief,
    )


class VerifyPatientRequest(BaseModel):
    patient_id: str

class VerifyPatientResponse(BaseModel):
    verified: bool
    session_id: str | None = None
    belief_state: dict | None = None
    patient_id: str | None = None
    message: str = ""

@router.post("/verify-patient", response_model=VerifyPatientResponse)
async def verify_patient(body: VerifyPatientRequest, request: Request):
    """Verify a returning patient by their KMG-XXXXXX ID. Zero LLM calls."""
    redis: aioredis.Redis = request.app.state.redis
    pid = body.patient_id.strip().upper()
    
    # Scan all patient profiles for matching ID
    cursor = 0
    while True:
        cursor, keys = await redis.scan(cursor, match="kyron:patient_profile:*", count=100)
        for key in keys:
            raw = await redis.get(key)
            if raw:
                profile = json.loads(raw)
                if profile.get("patient_id") == pid:
                    # Create a new session with pre-filled belief state
                    session_id = str(uuid.uuid4())
                    belief = {
                        "patient_id": profile["patient_id"],
                        "first_name": profile["first_name"],
                        "last_name": profile["last_name"],
                        "dob": profile.get("dob", ""),
                        "phone": profile.get("phone", ""),
                        "email": profile.get("email", ""),
                    }
                    session_data = {"messages": [], "belief_state": belief}
                    await save_session(redis, session_id, session_data)
                    return VerifyPatientResponse(
                        verified=True,
                        session_id=session_id,
                        belief_state=belief,
                        patient_id=pid,
                        message=f"Welcome back, {profile['first_name']}!",
                    )
        if cursor == 0:
            break
    
    return VerifyPatientResponse(verified=False, message="No patient found with that ID.")


class SendReminderRequest(BaseModel):
    phone: str | None = None
    email: str | None = None

class SendReminderResponse(BaseModel):
    sent: bool
    message: str
    masked_email: str | None = None

@router.post("/send-id-reminder", response_model=SendReminderResponse)
async def send_id_reminder(body: SendReminderRequest, request: Request):
    """Send a Patient ID reminder via SMS/email. Zero LLM calls."""
    redis: aioredis.Redis = request.app.state.redis
    
    # Look up by phone
    profile = None
    if body.phone:
        raw = await redis.get(f"kyron:patient_profile:{body.phone.strip()}")
        if raw:
            profile = json.loads(raw)
    
    # Fall back to scanning by email
    if not profile and body.email:
        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor, match="kyron:patient_profile:*", count=100)
            for key in keys:
                raw = await redis.get(key)
                if raw:
                    p = json.loads(raw)
                    if p.get("email", "").lower() == body.email.strip().lower():
                        profile = p
                        break
            if profile or cursor == 0:
                break
    
    if not profile or not profile.get("patient_id"):
        return SendReminderResponse(sent=False, message="No patient found with that contact info.")
    
    # Send via SMS + email
    from services.notifications import send_id_reminder_sms, send_id_reminder_email
    try:
        await send_id_reminder_sms(profile)
    except Exception:
        pass  # SMS may fail (test phone numbers)
    if profile.get("email"):
        await send_id_reminder_email(profile)
    
    # Mask email for display
    email = profile.get("email", "")
    if "@" in email:
        local, domain = email.split("@", 1)
        masked = local[:2] + "***@" + domain
    else:
        masked = None
    
    return SendReminderResponse(
        sent=True,
        message="A reminder with your Patient ID has been sent.",
        masked_email=masked,
    )


# ── Request / Response models ──────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    belief_state: dict
    booked_appointment: dict | None = None
    tool_calls_executed: list[str] = []


# ── Main endpoint ──────────────────────────────────────────────────────────────
@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request):
    redis: aioredis.Redis = request.app.state.redis
    session_id = body.session_id or str(uuid.uuid4())
    user_text = body.message
    return await process_chat_message(redis, session_id, user_text)


async def process_chat_message(redis: aioredis.Redis, session_id: str, user_text: str, is_voice: bool = False) -> ChatResponse:
    # Load session
    session_data = await get_session(redis, session_id)
    messages = session_data.get("messages", [])
    belief = session_data.get("belief_state", {})

    # Sanitize input
    user_text = sanitize_input(user_text)

    # Build system prompt with current context
    system = SYSTEM_PROMPT.format(
        current_date=date.today().strftime("%B %d, %Y"),
        belief_state=json.dumps(belief, indent=2) if belief else "No data collected yet.",
    )
    if is_voice:
        system += (
            "\n\n━━ VOICE RULES ━━\n"
            "Keep every single response to ONE or TWO short sentences maximum. "
            "Spell all numbers and dates in words. "
            "No markdown, no lists, no bullet points. "
            "Never provide medical advice. "
            "Be warm and natural like a receptionist on the phone."
        )

    messages.append({"role": "user", "content": user_text})

    # ── Low-Latency OpenAI-compatible Client (Groq/OpenRouter) ──
    from openai import AsyncOpenAI

    base_url = os.environ.get("LLM_BASE_URL")
    api_key = os.environ.get("LLM_API_KEY")
    model = os.environ.get("LLM_MODEL")

    if not base_url:
        if os.environ.get("GROQ_API_KEY"):
            base_url = "https://api.groq.com/openai/v1"
            api_key = os.environ.get("GROQ_API_KEY")
            # Groq requires specific model IDs. If the user left "kimi-k2.5" in their .env, override it.
            if not model or "llama" not in model.lower():
                model = "llama-3.3-70b-versatile"
        elif os.environ.get("OPENROUTER_API_KEY"):
            base_url = "https://openrouter.ai/api/v1"
            api_key = os.environ.get("OPENROUTER_API_KEY")
            if not model or "moonshot" not in model.lower():
                model = "moonshotai/kimi-k2:free"
        else:
            base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            api_key = os.environ.get("OLLAMA_API_KEY", "ollama")
            model = model or "kimi-k2.5:cloud"

    client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    # Cap message history to last 10 to control token count
    recent_messages = messages[-10:] if len(messages) > 10 else messages
    full_messages = [{"role": "system", "content": system}] + recent_messages
    tool_calls_executed = []
    final_reply = ""

    # Agentic loop — keep calling until no more tool calls or BLOCKED
    for iteration in range(5):  # Hard cap: max 5 LLM calls per user turn
        
        # Strip unsupported fields (like "reasoning" from DeepSeek) for strict endpoints like Groq
        safe_messages = []
        for m in full_messages:
            safe_messages.append({k: v for k, v in m.items() if k not in ("reasoning", "reasoning_content", "thought")})

        response = await client.chat.completions.create(
            model=model,
            messages=safe_messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.3,
        )

        msg = response.choices[0].message

        # ── Fallback for models that output tool calls in msg.content ──
        parsed_fn_name = None
        parsed_args = {}
        content_text = msg.content or ""
        text_before_tool = content_text
        
        if not msg.tool_calls and content_text.strip():
            lines = content_text.strip().split('\n')
            tool_names = [t["function"]["name"] for t in TOOLS]
            for i, line in enumerate(lines):
                line_clean = line.strip()
                if line_clean in tool_names:
                    parsed_fn_name = line_clean
                    text_before_tool = "\n".join(lines[:i]).strip()
                    rest = "\n".join(lines[i+1:]).strip()
                    
                    # Strip potential markdown blocks
                    if rest.startswith("```json"):
                        rest = rest[7:].strip()
                    elif rest.startswith("```"):
                        rest = rest[3:].strip()
                    if rest.endswith("```"):
                        rest = rest[:-3].strip()
                        
                    if rest.startswith("{") and rest.endswith("}"):
                        try:
                            parsed_args = json.loads(rest)
                        except Exception:
                            pass
                    break

        if msg.tool_calls:
            full_messages.append(msg.model_dump(exclude_none=True))
            blocked_this_round = False
            for tc in msg.tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments)
                tool_result, session_data = await execute_tool(fn_name, fn_args, session_data, redis)
                tool_calls_executed.append(fn_name)
                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_result,
                })
                # If the tool was BLOCKED due to missing fields, do ONE more LLM call to
                # let it formulate a polite ask-for-missing-info message, then stop.
                tool_result_obj = json.loads(tool_result)
                if tool_result_obj.get("error", "").startswith("BLOCKED"):
                    blocked_this_round = True
            belief = session_data.get("belief_state", {})
            if blocked_this_round:
                # One final LLM call to generate a user-facing message, then exit loop
                final_safe = [{k: v for k, v in m.items() if k not in ("reasoning", "reasoning_content", "thought")} for m in full_messages]
                blocked_response = await client.chat.completions.create(
                    model=model,
                    messages=final_safe,
                    temperature=0.3,
                )
                raw = blocked_response.choices[0].message.content or ""
                if "FINAL_ANSWER:" in raw:
                    final_reply = raw.split("FINAL_ANSWER:")[-1].strip()
                else:
                    final_reply = raw.strip()
                break
        elif parsed_fn_name:
            fake_call_id = f"call_{uuid.uuid4().hex[:8]}"
            
            # If the LLM said something before calling the tool, append it as assistant content
            if text_before_tool:
                full_messages.append({
                    "role": "assistant",
                    "content": text_before_tool
                })
                
            full_messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": fake_call_id,
                    "type": "function",
                    "function": {
                        "name": parsed_fn_name,
                        "arguments": json.dumps(parsed_args)
                    }
                }]
            })
            tool_result, session_data = await execute_tool(parsed_fn_name, parsed_args, session_data, redis)
            tool_calls_executed.append(parsed_fn_name)
            full_messages.append({
                "role": "tool",
                "tool_call_id": fake_call_id,
                "content": tool_result,
            })
            belief = session_data.get("belief_state", {})
        else:
            # No tool calls → this is the final response to the user
            final_reply = msg.content or ""
            
            # Strip FINAL_ANSWER: prefix if present (backwards compat)
            if "FINAL_ANSWER:" in final_reply:
                final_reply = final_reply.split("FINAL_ANSWER:")[-1].strip()
            
            break

    # Validate output safety
    is_safe, final_reply = validate_output(final_reply)

    # Append the final validated reply to the full_messages list
    if not (full_messages[-1]["role"] == "assistant" and full_messages[-1].get("content") == final_reply):
        full_messages.append({"role": "assistant", "content": final_reply})
        
    # Remove the system prompt before saving to session
    session_messages = [m for m in full_messages if m["role"] != "system"]
    session_data["messages"] = session_messages
    session_data["belief_state"] = belief

    # Register phone number for reconnect-on-callback
    if belief.get("phone"):
        await register_phone(redis, belief["phone"], session_id)

    # Persist session
    await save_session(redis, session_id, session_data)

    # Fire notifications if booking just happened
    pending = session_data.pop("pending_notifications", None)
    booked = session_data.get("booked_appointment")
    if pending:
        await send_confirmation_email(pending["patient"], pending["doctor"], pending["slot"])
        if pending["sms_opt_in"]:
            await send_confirmation_sms(pending["patient"], pending["doctor"], pending["slot"])
        await save_session(redis, session_id, session_data)

    return ChatResponse(
        reply=final_reply,
        session_id=session_id,
        belief_state=belief,
        booked_appointment=booked,
        tool_calls_executed=tool_calls_executed,
    )

@router.get("/session/{session_id}")
async def get_session_endpoint(session_id: str, request: Request):
    redis: aioredis.Redis = request.app.state.redis
    session_data = await get_session(redis, session_id)
    return {
        "messages": session_data.get("messages", []),
        "belief_state": session_data.get("belief_state", {}),
        "booked_appointment": session_data.get("booked_appointment"),
        "call_active": session_data.get("call_active", False)
    }
