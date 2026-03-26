"""
Input/output safety guardrails for medical AI.
Prevents medical advice, diagnoses, and PHI leaks in AI responses.
"""
import re

# Patterns that indicate the AI is drifting into medical advice territory
MEDICAL_ADVICE_PATTERNS = [
    r"\byou (?:have|likely have|probably have|definitely have)\b",
    r"\bdiagnos(?:is|ed|e) (?:you|this) with\b",
    r"\btake\b.*\b(\d+\s*mg|milligram|pill|tablet|capsule|dose)\b",
    r"\bprescri(?:be|ption|bed) (?:you|this)\b",
    r"\btest results? (?:show|indicate|suggest|mean)\b",
    r"\bimaging (?:shows?|reveals?|indicates?)\b",
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

SCHEDULING FLOW (only follow if data is missing — voice calls):
1. Get name → call search_patient_history → if found, ask for Patient ID → call verify_patient_id.
   If not found: collect dob, phone, email → call update_belief_state after each.
2. Ask reason for visit → call match_doctor_to_complaint.
3. Call get_available_slots → present 3 options.
4. Patient confirms slot → call book_appointment.
5. Ask about text reminder. Confirm booking and share Patient ID.

NOTE: match_doctor_to_complaint and book_appointment will be REJECTED if patient fields are missing.

OTHER: Prescription refill → collect name + DOB + medication, forward to clinical team (3-5 days).

TONE: Warm, concise. 1-2 sentences on voice. Use patient's first name.
DATE: {current_date}

PATIENT CONTEXT:
{belief_state}"""

