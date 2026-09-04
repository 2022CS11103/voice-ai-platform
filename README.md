# VelaVoice — Voice AI Agent Platform

Multi-tenant inbound **Voice AI Agent** platform for businesses.

Business owners create an AI receptionist, upload knowledge, connect a phone number, and let customers call in for natural conversations with RAG + tool calling (appointments, leads, human handoff).

## Stack

| Layer | Tech |
|--------|------|
| Frontend | Next.js 16 + TypeScript + Tailwind |
| Backend | FastAPI + Python |
| DB | SQLite (local MVP) or PostgreSQL + pgvector |
| STT + LLM | **Groq** (Whisper + Llama) — free tier |
| TTS | **Edge TTS** (free) via bundled ffmpeg |
| Telephony | Twilio Media Streams (bidirectional µ-law audio) |

## What's included (MVP modules)

- Authentication (JWT signup/login)
- Business dashboard
- Create / configure agents
- Knowledge / RAG (PDF, TXT, DOCX, CSV, website, manual text)
- Real phone calls (Twilio → Groq Whisper → Groq LLM + tools → Edge TTS)
- Tool calling (`search_knowledge_base`, `check_availability`, `book_appointment`, `cancel_appointment`, `create_lead`, `transfer_to_human`)
- Call history + transcripts
- Analytics

Demo vertical: **dental clinic receptionist** (ABC Dental / agent Sarah).

## Project structure

```
voice-ai-platform/
├── backend/          # FastAPI API + voice bridge
├── frontend/         # Next.js dashboard
├── docker-compose.yml
└── .env.example
```

## Quick start (local)

### 1. Get a free Groq API key

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up → **API Keys** → Create key (`gsk_...`)

### 2. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Edit `backend/.env`:

```env
GROQ_API_KEY=gsk_...
PORT=5050
PUBLIC_BASE_URL=https://YOUR_NGROK_URL
DATABASE_URL=sqlite+aiosqlite:///./voice_ai.db
TTS_VOICE=en-US-JennyNeural
```

Run:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 5050 --reload
```

Health check: [http://localhost:5050/health](http://localhost:5050/health)  
API docs: [http://localhost:5050/docs](http://localhost:5050/docs)

Seeded demo login:

- Email: `owner@abcdental.com`
- Password: `demo1234`

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### 4. Real phone calls

1. Start backend.
2. Expose it with ngrok:

```bash
ngrok http 5050
```

3. Set `PUBLIC_BASE_URL` in `backend/.env` to the ngrok HTTPS URL (no trailing slash). Restart backend.
4. In Twilio Console → Phone Numbers → your number → Voice webhook:

```
https://YOUR_NGROK_URL/telephony/incoming
```

Method: `HTTP POST`

5. Call the Twilio number. Flow:

```
Phone → Twilio Media Streams → Groq Whisper (STT)
      → Groq Llama + tools → Edge TTS → Twilio → Phone
```

## Optional: Postgres + pgvector

```bash
docker compose up -d db
```

Then in `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://voice:voice@localhost:5432/voice_ai
```

## Architecture (call path)

```
Customer phone
   ↓
Twilio Voice + Media Streams
   ↓  WebSocket (PCMU 8kHz)
FastAPI Voice bridge (VAD)
   ↓
Groq Whisper STT
   ↓
Groq LLM + tools (RAG, appointments, leads)
   ↓
Edge TTS → μ-law
   ↓
Twilio → caller
```

## Security notes

- Never put `GROQ_API_KEY` / Twilio secrets in frontend code.
- Keep secrets in `backend/.env` only.
- Enforce auth on dashboard APIs (JWT).
- Isolate data by `business_id` / ownership checks.

## Next phases (V2)

Outbound campaigns, CRM/calendar integrations, WhatsApp/SMS, live warm transfer, Stripe billing, multi-language, custom voices.
