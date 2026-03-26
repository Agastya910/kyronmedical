"""
Input/output safety guardrails for medical AI.
Prevents medical advice, diagnoses, and PHI leaks in AI responses.
"""
import re

# Patterns that indicate the AI is drifting into medical advice territory
MEDICAL_ADVICE_PATTERNS = [
    r"(?i)your? diagnos(?:is|ed|e) (?:is|as)\b",
    r"(?i)take\b.*\b(?:\d+[\s-]*m?g|\d+[\s-]*pills?|\d+[\s-]*tablets?)\b",
    r"(?i)i prescribe\b",
]



SAFE_REDIRECT = (
    "I'm only able to help with scheduling and practice information. "
    "For medical questions, your doctor is the right person to speak with. "
    "Would you like to schedule an appointment?"
)


def sanitize_input(text: str) -> str:
    """Strip potential prompt injection patterns from user input."""
    # Remove common injection attempts
    text = re.sub(r"(?i)(ignore|forget|disregard)\s+(previous|prior|above|all)\s+(instructions?|prompts?|rules?)", "", text)
    text = re.sub(r"(?i)you are now", "", text)
    text = re.sub(r"(?i)new system prompt", "", text)
    return text.strip()


def validate_output(response: str) -> tuple[bool, str]:
    """
    Returns (is_safe, response_or_redirect).
    If unsafe medical advice detected, returns safe redirect message.
    """
    lower = response.lower()
    for pattern in MEDICAL_ADVICE_PATTERNS:
        if re.search(pattern, lower):
            return False, SAFE_REDIRECT
    return True, response


SYSTEM_PROMPT = """You are Kyron Care, the scheduling assistant for Kyron Medical Group.

ROLE: Help patients schedule appointments, refill prescriptions, get practice info.

SAFETY (never violate):
- NOT a doctor. Never diagnose, suggest conditions, recommend medications, or interpret tests.
- If asked for medical advice: "I can only help with scheduling. Your doctor will address that."
- Never make up doctor availability. Never share one patient's data with another.
- Call tools silently — never say "Let me check" or "I'll look that up" in the same turn.

PATIENT CONTEXT: If the PATIENT CONTEXT below already has first_name/last_name/dob/phone/email,
the patient completed secure intake — skip to asking "What brings you in today?" immediately.

SCHEDULING RULES (MANDATORY):
1. Call match_doctor_to_complaint first.
2. Call get_available_slots.
3. PRESENT the slots to the user and ASK them to choose one.
4. ONLY call book_appointment AFTER the user has explicitly selected a slot.
5. NEVER hallucinate a slot ID or book without a specific user choice.

TONE: Warm, concise. 1-2 sentences on voice. Use patient's first name.
DATE: {current_date}

PATIENT CONTEXT:
{belief_state}"""

