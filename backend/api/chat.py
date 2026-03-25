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
            "description": "Semantically match the patient's chief complaint to the most appropriate doctor. Call this after collecting the reason for visit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chief_complaint": {
                        "type": "string",
                        "description": "Patient's stated reason for visit in their own words",
                    }
                },
                "required": ["chief_complaint"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_slots",
            "description": "Get available appointment slots for a doctor. Optionally filter by day of week.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_id": {"type": "string"},
                    "day_of_week": {
                        "type": "string",
                        "enum": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                        "description": "Optional: filter by specific day of week",
                    },
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
            "description": "Book a confirmed appointment. Call only after patient explicitly confirms the slot.",
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
                        "required": ["first_name", "last_name", "dob", "phone", "email"],
                    },
                    "sms_opt_in": {"type": "boolean", "default": False},
                },
                "required": ["doctor_id", "slot_id", "patient_info"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_practice_info",
            "description": "Get practice address, phone number, and hours of operation.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_belief_state",
            "description": "Update the structured patient belief state with newly collected information. Call silently after collecting any patient data field.",
            "parameters": {
                "type": "object",
                "properties": {
                    "updates": {
                        "type": "object",
                        "description": "Key-value pairs to merge into the patient belief state",
                    }
                },
                "required": ["updates"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_patient_history",
            "description": "Proactively search the long-term memory database for a returning patient's profile using their name or phone number.",
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
]


# ── Tool execution ─────────────────────────────────────────────────────────────
async def execute_tool(name: str, args: dict, session_data: dict, redis_client: aioredis.Redis) -> tuple[str, dict]:
    """Execute a tool call and return (result_json, updated_session_data)."""
    belief = session_data.get("belief_state", {})

    if name == "match_doctor_to_complaint":
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
        booking = {
            "doctor": doctor,
            "slot": target_slot,
            "patient": patient,
            "sms_opt_in": sms_opt_in,
        }
        belief.update({
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
            belief.update({
                "first_name": history.get("first_name", fname),
                "last_name": history.get("last_name", lname),
                "dob": history.get("dob", ""),
                "phone": history.get("phone", phone),
                "email": history.get("email", ""),
            })
            session_data["belief_state"] = belief
            return json.dumps({"found": True, "patient_data": history}), session_data
        else:
            return json.dumps({"found": False, "note": "No previous records found for this patient."}), session_data

    elif name == "update_belief_state":
        updates = args.get("updates", {})
        belief.update(updates)
        session_data["belief_state"] = belief
        
        # If we now have contact info, save/update the profile early
        if belief.get("first_name") and belief.get("last_name") and belief.get("phone"):
            p_dict = {
                "first_name": belief.get("first_name"),
                "last_name": belief.get("last_name"),
                "dob": belief.get("dob"),
                "phone": belief.get("phone"),
                "email": belief.get("email"),
            }
            await redis_client.set(f"kyron:patient_profile:{p_dict['first_name'].lower().strip()}_{p_dict['last_name'].lower().strip()}", json.dumps(p_dict))
            await redis_client.set(f"kyron:patient_profile:{p_dict['phone'].strip()}", json.dumps(p_dict))
            
        return json.dumps({"updated": True, "note": "Belief state updated."}), session_data

    return json.dumps({"error": "Unknown tool"}), session_data


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

    # ── OpenAI-compatible Client for Ollama Cloud ──
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        base_url=os.environ.get("OLLAMA_BASE_URL", "https://ollama.com/v1"),
        api_key=os.environ.get("OLLAMA_API_KEY", "ollama")
    )
    model = os.environ.get("LLM_MODEL", "deepseek-v3.1:671b-cloud")

    full_messages = [{"role": "system", "content": system}] + messages
    tool_calls_executed = []
    final_reply = ""

    # Agentic loop — keep calling until no more tool calls
    for _ in range(10):  # safety limit
        response = await client.chat.completions.create(
            model=model,
            messages=full_messages,
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
            belief = session_data.get("belief_state", {})
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
            final_reply = msg.content or ""
            
            # Extract final answer
            reply_text = final_reply
            if final_reply.startswith("FINAL_ANSWER:"):
                reply_text = final_reply[len("FINAL_ANSWER:"):].strip()
            elif "FINAL_ANSWER:" in final_reply:
                reply_text = final_reply.split("FINAL_ANSWER:")[-1].strip()
                
            if "FINAL_ANSWER:" in final_reply:
                final_reply = reply_text
                break
            else:
                # Agent did not use FINAL_ANSWER and didn't call a tool.
                full_messages.append({"role": "assistant", "content": final_reply})
                full_messages.append({"role": "user", "content": "You did not execute a tool nor did you provide a FINAL_ANSWER: prefix. If you need to search or check something, execute a tool NOW. If you are ready to speak to the user, strictly prefix your message with FINAL_ANSWER:."})
                continue

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
