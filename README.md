# Kyron Care — Patient Scheduling Web App

A production-quality AI-powered patient scheduling assistant for Kyron Medical Group.

## Tech Stack
- Frontend: Next.js 14 + TypeScript + Tailwind CSS (Liquid Glass UI) + Framer Motion
- Backend: FastAPI (Python) + uv package manager
- LLM: Kimi K2.5 via Ollama (OpenAI-compatible API)
- Embeddings: BGE-M3 (BAAI) via sentence-transformers — semantic doctor matching
- Voice AI: Vapi (outbound + inbound phone with full context handoff)
- Session store: Redis
- Notifications: SendGrid (email) + Twilio (SMS)
- Hosting: AWS EC2 + Nginx + Let's Encrypt

## Local Development

### Prerequisites
- Python 3.11+, Node.js 18+, Redis, uv, Ollama

### 1. Clone and configure
    git clone YOUR_REPO
    cd kyron-medical

### 2. Backend
    cd backend
    cp .env.example .env   # fill in API keys
    uv sync
    uv run uvicorn main:app --reload --port 8000

### 3. Pull Kimi K2.5
    ollama pull hf.co/bartowski/Kimi-K2-Instruct-GGUF:Q4_K_M
    ollama serve

### 4. Frontend
    cd frontend
    cp .env.example .env.local
    npm install
    npm run dev

App runs at http://localhost:3000
