# BARTA ai — Autonomous Outbound AI Voice Agent Platform

> **Submission for The Great Indian AI Internship Challenge**  
> **Challenge Deadline:** November 10, 2026, 11:59 PM IST  
> **Pitch:** *Upload a customer list, press start, and watch orders arrive on your dashboard.*

---

## 1. Overview & Problem Statement

Small and mid-size Indian businesses lose high-intent sales because follow-up calls are slow, inconsistent, and expensive. Owners lack visibility into what callers promised, who asked to be called later, or whether leads were contacted on time.

**BARTA ai** automates outbound sales calls end-to-end:
- **Speaks naturally** in **Hindi, English, and Hinglish** with sub-1.5s latency.
- **Transcribes caller audio in real-time** with **Gnani Prisma STT** (`wss://api.vachana.ai/stt/v3/stream`).
- **Synthesizes voice replies** with **Gnani Timbre TTS** (`v2.0`).
- **Orchestrates intelligent sales qualification** with **Google Gemini 2.5 Flash / Flash-Lite** under strict guardrails.
- **Executes real-time tools**:
  - `confirm_order(product, quantity, email)`: Generates single-use 72h token and emails secure delivery details form.
  - `schedule_callback(due_at_iso, reason)`: Respects promises ("call me in 2 days") and queues callbacks inside allowed calling windows (IST).
  - `set_outcome(outcome, notes)`: Records `order_confirmed`, `interested`, `callback_requested`, `not_interested`, `no_answer`, or `do_not_call`.
- **Delivers a clean Apple-inspired dashboard** showing the sales funnel, headline counters, transcripts, orders, and callbacks.

**Demo Showcase Product:** [CURATED India](https://curatedindia.vercel.app) — Handcrafted minimalist linen festive collection.

---

## 2. Gnani AI Models & Telephony Integration

| Component | Technology | Role in BARTA ai |
|---|---|---|
| **STT (Speech-to-Text)** | **Gnani Prisma (v2.5 / v3)** | Real-time streaming transcription over WebSocket (`wss://api.vachana.ai/stt/v3/stream`). Processes 8 kHz 16-bit linear PCM audio. Supports Indian code-mixed speech (Hindi, English, Hinglish). |
| **TTS (Text-to-Speech)** | **Gnani Timbre (v2.0)** | Natural neural Indian voice synthesis. Output converted from 16-bit linear PCM to 8 kHz μ-law for telephony delivery. |
| **LLM Reasoning** | **Google Gemini 2.5 Flash** | Conversational dialogue turns, strict product guardrails (never invents prices or sizes), and tool calling. |
| **Telephony** | **Twilio Programmable Voice** | Bidirectional Media Streams WebSocket (`/twilio/media`) over 8 kHz μ-law audio. Barge-in interruption support via Twilio `clear` event. |
| **Order Details & Email** | **Resend / SMTP Fallback** | Dispatches single-use delivery details links with 72-hour cryptographic tokens. |
| **Backend & Concurrency** | **FastAPI (Python 3.11)** | Non-blocking asynchronous queue, atomic contact locking, IST window checker, and background scheduler. |
| **Frontend Dashboard** | **Next.js 14 (App Router) + Tailwind** | Apple-inspired minimal UI with live counters, conversion funnel, transcript drawer, and interactive browser simulator. |

---

## 3. Audio Pipeline Architecture

```mermaid
flowchart LR
    Caller["Customer Phone"] <-->|8kHz μ-law| Twilio["Twilio Media Stream"]
    Twilio <-->|WebSocket| Converter["Audio Converter (mulaw <-> pcm16)"]
    Converter -->|8kHz 16-bit PCM| Prisma["Gnani Prisma STT"]
    Prisma -->|Final Transcript| Gemini["Gemini 2.5 LLM + Tools"]
    Gemini -->|Spoken Text| Timbre["Gnani Timbre TTS"]
    Timbre -->|Linear PCM| Converter
    Converter -->|8kHz μ-law frames| Twilio
    Gemini -->|confirm_order| DB["Supabase / SQLite"]
    DB -->|Order Email| Customer["Customer Form Link"]
```

---

## 4. Project Directory Structure

```
BARTA AI 2/
├── backend/
│   ├── app/
│   │   ├── config.py              # Environment settings & credentials
│   │   ├── database.py            # Async SQLAlchemy engine & seed products
│   │   ├── models.py              # PostgreSQL/SQLite models
│   │   ├── main.py                # FastAPI entry point & lifespan
│   │   ├── services/
│   │   │   ├── audio_converter.py # Twilio 8kHz μ-law <-> 16-bit PCM codec
│   │   │   ├── gnani_stt.py       # Gnani Prisma WebSocket streaming STT
│   │   │   ├── gnani_tts.py       # Gnani Timbre neural voice TTS
│   │   │   ├── llm_agent.py       # Gemini prompt & tool orchestrator
│   │   │   ├── dispatcher.py      # Concurrency controller (1 or 3-5 calls)
│   │   │   ├── scheduler.py       # 60s background IST callback worker
│   │   │   ├── order_service.py   # 72h single-use token order manager
│   │   │   ├── email_service.py   # Resend & SMTP HTML email dispatcher
│   │   │   └── twilio_service.py  # Twilio outbound dialer & TwiML generator
│   │   └── routers/
│   │       ├── campaigns.py       # Campaign CRUD, stats, CSV import
│   │       ├── calls.py           # Call logs & transcript drawer
│   │       ├── orders.py          # Orders pipeline
│   │       ├── callbacks.py       # Callbacks list, reschedule, cancel
│   │       ├── public_forms.py    # Public customer order fulfillment form
│   │       ├── twilio_media.py    # /twilio/voice webhook & WS /twilio/media
│   │       └── simulator.py       # Browser-based live voice simulator
│   ├── data/
│   │   └── sample_contacts.csv    # Demo contacts for import
│   ├── requirements.txt           # Python dependencies
│   ├── test_backend.py            # Unit tests for dialogue & DB
│   └── test_e2e.py                # 12-step full pipeline acceptance test
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx           # Overview Dashboard & conversion funnel
│   │   │   ├── campaigns/page.tsx # Campaigns & CSV import modal
│   │   │   ├── calls/page.tsx     # Calls list & transcript drawer
│   │   │   ├── orders/page.tsx    # Orders table & form links
│   │   │   ├── callbacks/page.tsx # Scheduled callbacks in IST
│   │   │   ├── simulator/page.tsx # Interactive voice agent simulator
│   │   │   └── order-form/[token]/page.tsx # Hosted customer delivery form
│   │   ├── components/            # Sidebar, Navbar, AppShell
│   │   └── lib/api.ts             # Typed API client
│   └── package.json               # Next.js 14 + Tailwind configuration
├── PRD.md                         # Product Requirements Document v1.0
└── README.md                      # Complete setup and evaluation guide
```

---

## 5. Quick Start Guide

### Step 1: Start the Backend (FastAPI)

1. Open a terminal in `backend/`:
   ```bash
   cd backend
   # Virtual environment is already prepared in backend/venv
   .\venv\Scripts\activate
   ```
2. Configure credentials in `backend/.env` (Twilio, Gnani AI, Gemini, Resend):
   ```env
   GNANI_API_KEY=your_gnani_key
   GNANI_STT_WS_URL=wss://api.vachana.ai/stt/v3/stream
   GNANI_TTS_API_URL=https://api.vachana.ai/tts/v2/synthesize
   GEMINI_API_KEY=your_gemini_key
   TWILIO_ACCOUNT_SID=your_twilio_sid
   TWILIO_AUTH_TOKEN=your_twilio_token
   TWILIO_PHONE_NUMBER=+1...
   TWILIO_WEBHOOK_URL=https://your-tunnel.ngrok-free.app
   ```
   *(Note: If API keys are not supplied, BARTA automatically runs in rich simulation mode so you can evaluate the complete pipeline without credit exhaustion).*

3. Run the backend server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   Backend will be running at `http://localhost:8000` with Swagger docs at `http://localhost:8000/docs`.

### Step 2: Start the Frontend Dashboard (Next.js)

1. Open a second terminal in `frontend/`:
   ```bash
   cd frontend
   npm run dev
   ```
2. Open `http://localhost:3000` in your browser.

---

## 6. How to Test the Demo (Evaluator Guide)

### Option A: Using the Built-In Voice Simulator (Instant, No Twilio Setup Needed)
1. Navigate to **Voice Simulator** (`http://localhost:3000/simulator`) on the dashboard.
2. Click **Start Simulated Voice Call**.
3. BARTA will greet you:
   > *"Namaste Aarav Sharma ji! Main BARTA automated assistant bol raha hoon CURATED India se. Kya abhi baat karne ke liye 2 minute ka samay hai?"*
4. Click on quick prompts or type custom turns in Hindi, English, or Hinglish:
   - *"Price kya hai aur koi festive offer hai kya?"*
   - *"Theek hai ek piece order confirm kar do COD pe."*
5. Watch BARTA execute the tool `confirm_order`, output the response, and generate the order.
6. Open **Orders** on the dashboard to see the new order. Click **Open Form** to view the customer delivery details page!

### Option B: Running the Automated E2E Test Suite
Run the 12-step automated pipeline verification script:
```bash
$env:PYTHONIOENCODING="utf-8"
$env:PYTHONPATH="backend"
backend\venv\Scripts\python backend\test_e2e.py
```
Outputs `🏆 ALL 12 END-TO-END PIPELINE CHECKS PASSED! 🏆`.

### Option C: Live Phone Call via Twilio
1. Start an ngrok tunnel pointing to port 8000:
   ```bash
   ngrok http 8000
   ```
2. Put the ngrok URL into `TWILIO_WEBHOOK_URL` in `backend/.env`.
3. Go to **Campaigns**, click **Import CSV**, upload `backend/data/sample_contacts.csv`, and press **Start Calling**.
4. Twilio will dial your phone, stream audio to `/twilio/media`, transcribe via **Gnani Prisma**, converse via **Gemini**, and speak via **Gnani Timbre**!

---

## 7. Contest Submission Checklist (Nov 10, 2026)

- [x] **Project Title:** BARTA ai
- [x] **Problem Statement & Users:** Clear B2B/B2C outbound sales automation for small Indian businesses.
- [x] **Gnani AI Models Used:**
  - Prisma STT (v2.5 / v3) for real-time multilingual transcription
  - Timbre TTS (v2.0) for low-latency voice synthesis
- [x] **E2E Working Application:** Call placed -> voice confirmed -> dashboard updated -> order email dispatched -> callback scheduled in IST.
- [x] **Demo Product:** [CURATED India](https://curatedindia.vercel.app)
- [x] **Synthetic Data Only:** Zero real customer PII used; verified test contacts only.

