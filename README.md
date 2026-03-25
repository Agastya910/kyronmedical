# Kyron Care — AI-Powered Patient Scheduling Assistant

**A production-quality, fully autonomous patient scheduling system for Kyron Medical Group, featuring both interactive Web Chat and a real-time Voice telephony pipeline.** 

This project is a detailed take-home challenge submission, showcasing an end-to-end intelligent AI agent capable of understanding real-time conversational context, persistent long-term patient memory, semantic practitioner matching, and dynamic voice synthesis—all while leveraging a cost-effective, open-source-first architecture.

## 🌟 Key Features & Architectural Highlights

### 1. Cost-Effective "Free Voice" Pipeline
To achieve a highly scalable, zero-to-low-cost audio pipeline, we fully migrated from expensive, paid conversational layers (like OpenAI Realtime API or Vapi) to a custom-built, highly optimized stack:
- **Speech-to-Text (STT)**: **Deepgram** (Free Tier) to rapidly convert Twilio telephony audio into text.
- **Intelligence (LLM)**: **Ollama** running **Kimi K2.5** locally, ensuring zero API token costs per inference.
- **Text-to-Speech (TTS)**: **edge-tts** for completely free, low-latency, and natural-sounding voice generation.
- **Telephony**: **Twilio** webhooks integrated directly into the FastAPI backend (`backend/api/webhook.py` and `backend/api/voice_stream.py`) to manage bi-directional audio streams and contextual AI handoffs.

### 2. Explicit Agentic Memory System
Rather than relying on hidden, static database lookups behind the scenes, we upgraded the agent to function as a first-class autonomous entity with *Reactive Agentic Memory*:
- The AI autonomously utilizes a `search_patient_history` tool during patient intake.
- This allows the AI to proactively query long-term storage, recall past appointments, ongoing treatments, or prior physician preferences seamlessly in real time.
- **Result:** Returning patients receive a highly personalized, context-aware experience that mimics a true, seasoned medical receptionist who "remembers" them and their medical history.

### 3. Intelligent RAG & Semantic Doctor Matching
- Uses **BGE-M3** (BAAI) via `sentence-transformers` for deep semantic embeddings.
- When a patient describes their symptoms (e.g., "my knee hurts when running"), the `matcher.py` engine semantically aligns their needs with the correct specialist's expertise and schedule, not just basic keyword matching.

### 4. Robust API & Enterprise Guardrails
- **Backend API**: Built on **FastAPI** (Python 3.11+) and managed via the blazing-fast `uv` package manager.
- **Agent Guardrails**: Integrated safety checks (`guardrails.py`) ensure the LLM strictly adheres to scheduling constraints, blocking hallucinations of fake appointments or unsafe medical advice.
- **Session State**: **Redis** manages ongoing real-time chat and voice session state (`session.py`).
- **Notifications**: Automatic SMS via **Twilio** and Email via **Sendgrid** confirm appointments securely (`notifications.py`).

### 5. Liquid Glass Web App
- **Frontend**: Next.js 14, React 18, and TypeScript.
- **UI/UX**: Tailwind CSS combined with Framer Motion creates a stunning, responsive "Liquid Glass" aesthetic that feels modern, premium, and state-of-the-art.

---

## 🛠️ Tech Stack Summary

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 14, React, TypeScript, Tailwind CSS, Framer Motion |
| **Backend API** | Python, FastAPI, `uv` package manager |
| **Local LLM** | Ollama, Kimi K2.5 (`hf.co/bartowski/Kimi-K2-Instruct-GGUF:Q4_K_M`) |
| **Voice Stack** | Twilio (Routing), Deepgram (STT), `edge-tts` (TTS), `pydub`/`ffmpeg` |
| **Embeddings** | `sentence-transformers`, BGE-M3 (BAAI) |
| **Infrastructure** | Redis (State), Nginx, AWS EC2, Let's Encrypt |

---

## 💻 Local Development Setup

### Prerequisites
- Python 3.11+, Node.js 18+, Redis, `uv` package manager, and `Ollama`.
- Ensure `ffmpeg` is installed for audio stream processing:
  - **Windows**: `winget install ffmpeg` 
  - **Mac**: `brew install ffmpeg`
  - **Ubuntu**: `sudo apt install -y ffmpeg`

### 1. Clone & Configure
```bash
git clone https://github.com/Agastya910/kyronmedical.git
cd kyronmedical
```

### 2. Backend Initialization
The backend relies on `uv` for lightning-fast dependency resolution.
```bash
cd backend
cp .env.example .env 
```
**API Keys setup in `.env`**:
- **Deepgram API Key** (Free Tier: `DEEPGRAM_API_KEY`)
- **Twilio Credentials** (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`)
- **Ngrok Base URL** (for local Twilio webhook testing: `SERVER_BASE_URL=https://<your-ngrok-url>`)

```bash
uv sync
uv run uvicorn main:app --reload --port 8000
```

### 3. Local LLM Setup (Ollama)
Pull the Kimi K2.5 Instruct model for the local LLM agent to begin local inferencing.
```bash
ollama pull hf.co/bartowski/Kimi-K2-Instruct-GGUF:Q4_K_M
ollama serve
```

### 4. Frontend Initialization
```bash
cd ../frontend
cp .env.example .env.local
npm install
npm run dev
```
The full application will now be running at [http://localhost:3000](http://localhost:3000).

---

## 📞 Testing the Voice Pipeline
1. Boot up `ngrok`: `ngrok http 8000`
2. Update your `.env` with the `SERVER_BASE_URL` from ngrok.
3. Configure your Twilio Phone Number's **"A call comes in"** webhook to point to:
   `https://<your-ngrok-url>/api/webhook/twilio` (HTTP POST).
4. Call the Twilio number. The system will answer, Deepgram will transcribe the audio natively, Ollama will process intent, and `edge-tts` will dynamically synthesize the agent's response over the phone in real time.

---
*Built as a functional prototype demonstrating cost-efficient Local AI architectures, real-time voice synthesis, and explicit tool-calling memory design for medical applications.*
