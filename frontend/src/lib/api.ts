const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ChatResponse {
  reply: string;
  session_id: string;
  belief_state: Record<string, unknown>;
  booked_appointment: BookedAppointment | null;
  tool_calls_executed: string[];
}

export interface BookedAppointment {
  doctor: { name: string; specialty: string; photo_placeholder: string };
  slot: { display_date: string; time: string; date: string };
  patient: { first_name: string; last_name: string; email: string; phone: string };
}

export async function sendMessage(message: string, sessionId: string | null): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!res.ok) throw new Error(`Chat API error: ${res.status}`);
  return res.json();
}

export async function initiateCall(phoneNumber: string, sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/initiate-call`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone_number: phoneNumber, session_id: sessionId }),
  });
  if (!res.ok) throw new Error(`Call API error: ${res.status}`);
}

export async function getSession(sessionId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/session/${sessionId}`);
  if (!res.ok) throw new Error(`Session fetch error: ${res.status}`);
  return res.json();
}

// ── Deterministic Intake APIs (zero LLM calls) ──

export interface IntakeResponse {
  patient_id: string;
  session_id: string;
  belief_state: Record<string, unknown>;
}

export async function submitPatientIntake(data: {
  first_name: string;
  last_name: string;
  dob: string;
  phone: string;
  email: string;
}): Promise<IntakeResponse> {
  const res = await fetch(`${API_BASE}/api/patient-intake`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Intake error: ${res.status}`);
  return res.json();
}

export interface VerifyResponse {
  verified: boolean;
  session_id: string | null;
  belief_state: Record<string, unknown> | null;
  patient_id: string | null;
  message: string;
}

export async function verifyPatient(patientId: string): Promise<VerifyResponse> {
  const res = await fetch(`${API_BASE}/api/verify-patient`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ patient_id: patientId }),
  });
  if (!res.ok) throw new Error(`Verify error: ${res.status}`);
  return res.json();
}

export interface ReminderResponse {
  sent: boolean;
  message: string;
  masked_email: string | null;
}

export async function sendIdReminder(phone?: string, email?: string): Promise<ReminderResponse> {
  const res = await fetch(`${API_BASE}/api/send-id-reminder`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone: phone || null, email: email || null }),
  });
  if (!res.ok) throw new Error(`Reminder error: ${res.status}`);
  return res.json();
}
