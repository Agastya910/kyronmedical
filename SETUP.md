## Free Voice Stack Setup

### 1. Deepgram (Speech-to-Text & Text-to-Speech) — Free, no credit card
- Go to https://deepgram.com → "Start for Free" → sign up with email
- Dashboard → API Keys → Create Key → copy it
- Paste into backend/.env as: DEEPGRAM_API_KEY=your_key
- You get $200 free credit (~43,000 minutes of audio)
- Deepgram now powers both our real-time hearing (STT) and real-time voice (Aura TTS) without needing `ffmpeg`!

### 2. Groq (Low-Latency LLM) — Free, no credit card
- Voice requires sub-second latency. The free Ollama cloud cluster is too slow for phone calls.
- Go to https://console.groq.com → sign in
- API Keys → Create API Key
- Paste into backend/.env as: GROQ_API_KEY=your_groq_key
- This instantly hooks up the lightning-fast `llama-3.3-70b-versatile` model.

### 4. Twilio (Phone calls) — $15 free trial, no card required initially
- Go to https://twilio.com → sign up
- Console → copy Account SID and Auth Token → paste into backend/.env
- Phone Numbers → Manage → Get a free trial number
- Paste number into TWILIO_PHONE_NUMBER in .env
- Phone Numbers → your number → Voice Configuration:
  - "A call comes in" → Webhook → https://YOUR_DOMAIN/api/webhook/twilio → HTTP POST
  - Save

### 5. ngrok (for local dev only — makes your localhost public for Twilio webhooks)
- Download from https://ngrok.com/download
- Run: ngrok http 8000
- Copy the https URL (e.g. https://abc123.ngrok-free.app)
- Paste into backend/.env as: SERVER_BASE_URL=https://abc123.ngrok-free.app
- On EC2: SERVER_BASE_URL=https://your-actual-domain.com

### 6. Restart backend after filling in all keys
- uv run uvicorn main:app --reload --port 8000
