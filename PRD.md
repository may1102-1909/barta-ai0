# BARTA ai: Product Requirements Document

**Version:** 1.0  
**Date:** Oct 30, 2026  
**Event:** Built for the Great Indian AI Internship Challenge (Submission deadline Nov 10, 2026, 11:59 PM IST)  
**Audience:** Full-stack developer handoff  

---

## 1. Overview
BARTA ai is an outbound AI voice agent platform for B2B and B2C sales. A business uploads a list of customers. The agent phones each one, holds a natural conversation (Hindi, English, Hinglish), qualifies interest, confirms orders, schedules callbacks and follows up over email and WhatsApp. Every outcome flows into a live dashboard so the owner sees exactly what happened without listening to a single call.

The product runs on **Gnani AI models** (**Prisma** for speech-to-text, **Timbre** for text-to-speech), which is a hard requirement of the challenge.

**One-line pitch:** Upload a customer list, press start, and watch orders arrive on your dashboard.

---

## 2. Problem and Goals
### Problem
Small and mid-size Indian businesses lose sales because follow-up calls are slow, inconsistent and expensive. Owners cannot see what callers promised, who asked to be called later, or how many people were actually reached.

### Goals
- Automate outbound calling end to end: dial, converse, capture the outcome.
- Give the owner a single dashboard with complete visibility: calls made, connected, interested, orders confirmed, callbacks pending.
- Convert interest into a paid order through email (and optionally WhatsApp) without human effort.
- Remember callback promises (“call me in 2 days”) and honor them automatically.
- Ship a working, demo-ready product by Nov 10, 2026.

### Non-goals (v1)
- Inbound call handling
- Multi-tenant billing, user roles or team management
- Real payment settlement (test mode only)
- Production WhatsApp Business onboarding and template approval
- Languages beyond Hindi, English and Hinglish

---

## 3. Users
| Persona | Description | Needs |
|---|---|---|
| **Owner (primary)** | Runs a small business or sales team | Upload a list, start a campaign, see results and orders at a glance |
| **Customer (secondary)** | Person receiving the call | Short, polite, natural call; easy way to say yes, no or later; simple order form |
| **Developer (internal)** | Builds and maintains the system | Clear architecture, observable calls, replayable transcripts |

**Demo product:** **CURATED** (`curatedindia.vercel.app`), the owner’s own fashion e-commerce site, is used as the product the agent sells during testing and the demo.

---

## 4. Scope

### MVP (must ship)
- Contact list upload (CSV) and campaign creation
- Outbound calling via Twilio with real-time voice loop (Prisma → LLM → Timbre)
- Structured call outcomes saved to the database
- Owner dashboard: funnel, calls, orders, callbacks, transcripts
- Order confirmation by voice, followed by an email with an order and delivery details form
- Callback scheduling and automatic re-dial
- Configurable concurrency (one at a time or several at once)

### Stretch (only if time allows)
- WhatsApp: send product info and payment link after a call; answer inbound product questions
- Live call status on the dashboard (realtime updates)
- Test-mode payment link (Razorpay test mode)
- Sentiment and language tags per call

### Out of scope
Everything listed under non-goals.

---

## 5. Key User Flows

### Flow A: Campaign run
1. Owner uploads a CSV (name, phone, preferred language) and picks the product.
2. Owner sets max concurrent calls, calling window and retry rules, then presses Start.
3. The queue dials contacts. Each call is handled by the voice agent.
4. When a call ends, the outcome, summary and transcript are saved and the dashboard updates.

### Flow B: Order confirmation
1. Customer says they want the product.
2. Agent confirms product, quantity and the email address, then calls `confirm_order`.
3. System creates an order with status `awaiting_details` and emails the customer a secure link.
4. Customer fills in delivery address and chooses a payment option on the form page.
5. Order status moves to `details_received`, then `paid` (test mode) or `cod`.
6. Owner sees every status change on the dashboard.

### Flow C: Callback
1. Customer says “revert to me in 2 days”.
2. Agent calls `schedule_callback` with an exact date and time in IST.
3. The scheduler re-queues the contact when the time arrives, inside the allowed calling window.
4. On the second call the agent opens with context from the previous call.

### Flow D: WhatsApp (stretch)
1. After a call, the agent sends product details or a payment link on WhatsApp.
2. Customer can reply with questions (“what sizes?”, “where is my order?”) and the same LLM answers from product and order data.
3. A customer can also request a callback by message, which creates a row in the callbacks table.

---

## 6. Functional Requirements

### 6.1 Campaigns and contacts
| ID | Requirement | Priority |
|---|---|---|
| FR-1 | Import contacts from CSV (name, phone in E.164, language, optional notes). Reject invalid rows with a clear message. | Must |
| FR-2 | Create a campaign with a product, goal text, max concurrent calls, calling window and retry limit. | Must |
| FR-3 | Start, pause and stop a campaign. Stop must end new dialing immediately and let active calls finish. | Must |
| FR-4 | Mark contacts as do-not-call when requested on a call. Never dial them again. | Must |

### 6.2 Voice agent
| ID | Requirement | Priority |
|---|---|---|
| FR-5 | Place outbound calls through Twilio Programmable Voice and stream audio over a bidirectional Media Stream WebSocket. | Must |
| FR-6 | Transcribe caller speech in real time with Gnani Prisma. | Must |
| FR-7 | Generate replies with an LLM (cloud model or local Ollama model) using campaign, product and contact context. | Must |
| FR-8 | Speak replies with Gnani Timbre, streamed back to Twilio. | Must |
| FR-9 | Support barge-in: if the customer starts speaking, stop agent audio and listen. | Should |
| FR-10 | Converse in Hindi, English and Hinglish, matching the customer’s language. | Must |
| FR-11 | Handle no-answer, busy and voicemail. Retry up to the campaign limit, spaced at least 2 hours apart. | Must |
| FR-12 | Disclose at the start of the call that it is an automated assistant. | Must |
| FR-13 | End every call by recording exactly one outcome: `order_confirmed`, `interested`, `callback_requested`, `not_interested`, `no_answer`, `wrong_number` or `do_not_call`. | Must |
| FR-14 | Save the full transcript and a 2 to 3 sentence summary after each call. | Must |

### 6.3 Agent tools (LLM function calls)
- `confirm_order(product, quantity, email)`: Creates an order and triggers the details email
- `schedule_callback(due_at_iso, reason)`: Stores a callback with an exact IST datetime
- `send_email(type)`: Sends a payment or delivery details email
- `send_whatsapp(message_type)`: Sends product info or a payment link (stretch)
- `set_outcome(outcome, notes)`: Records the final call outcome

*Guardrail:* The LLM must never invent prices, stock or delivery dates. Product facts come only from the product record provided in the prompt.

### 6.4 Orders and email
| ID | Requirement | Priority |
|---|---|---|
| FR-15 | On `confirm_order`, create an order with status `awaiting_details` and a unique, unguessable form token. | Must |
| FR-16 | Send an email with order summary and a link to a hosted form (name, delivery address, pincode, payment choice). | Must |
| FR-17 | When the form is submitted, update the order and show the change on the dashboard. | Must |
| FR-18 | Form links expire after 72 hours and can be used once. | Should |
| FR-19 | Test-mode payment link (Razorpay test mode) or cash on delivery option. | Could |

### 6.5 Callbacks
| ID | Requirement | Priority |
|---|---|---|
| FR-20 | Store each callback with contact, `due_at` (timestamp with time zone), reason and status (`pending`, `in_progress`, `done`, `cancelled`). | Must |
| FR-21 | A scheduler checks every minute for due callbacks and adds them to the dial queue. | Must |
| FR-22 | If a callback falls outside the calling window, move it to the next window opening. | Must |
| FR-23 | The callback call receives the previous summary and the callback reason as context. | Must |
| FR-24 | The dashboard lists upcoming callbacks and lets the owner cancel or reschedule one. | Should |

### 6.6 WhatsApp (stretch)
| ID | Requirement | Priority |
|---|---|---|
| FR-25 | Send product info and payment or form links to a customer on WhatsApp after a call. | Could |
| FR-26 | Answer inbound product and order questions using the same LLM with the same guardrails. | Could |
| FR-27 | Log every message in the messages table and show it in the contact timeline. | Could |

*Note:* Use Twilio WhatsApp sandbox for demo.

### 6.7 Dashboard
| ID | Requirement | Priority |
|---|---|---|
| FR-28 | Overview page with funnel: contacts → called → connected → interested → order confirmed. | Must |
| FR-29 | Headline counters: total calls made, connected calls, orders confirmed, callbacks pending, average call duration. | Must |
| FR-30 | Calls table with filters (campaign, outcome, date). Row opens transcript, summary and outcome. | Must |
| FR-31 | Orders table with status and detail view. | Must |
| FR-32 | Callbacks view (upcoming and past). | Must |
| FR-33 | Live updates without page refresh (Supabase Realtime / WebSocket). | Could |
| FR-34 | Export campaign report as CSV. | Could |

---

## 7. Call Concurrency
- `max_concurrent` on the campaign:
  - `1` (default for testing and demo): one call at a time.
  - `3` to `5` (scale mode): several calls in parallel.
- Rules:
  - Atomic mark of contact state (`dialing`) before dispatch.
  - Dispatcher fills free slots as calls finish.
  - Respect Twilio limits & Gnani balance.
  - Respect calling window.

---

## 8. System Architecture
- **Frontend:** Next.js (Tailwind CSS, Lucide Icons, Apple-inspired clean UI) & Public order form page.
- **Backend:** FastAPI (Python 3.11) with WebSocket endpoint `/twilio/media`, webhooks, campaign dispatcher, callback scheduler.
- **Database:** Supabase (PostgreSQL) + Realtime, with robust local fallback for standalone execution.
- **Telephony:** Twilio Programmable Voice + Media Streams (8 kHz audio).
- **Speech:** Gnani Prisma (STT - `wss://api.vachana.ai/stt/v3/stream`, 8kHz/16kHz PCM), Gnani Timbre (TTS).
- **LLM:** Google Gemini API (Flash-Lite / fast model) with tool calling.
- **Email:** Resend / SMTP fallback.
- **Audio pipeline:**
  - Twilio 8kHz μ-law (PCMU) <-> 8kHz 16-bit linear PCM (Prisma STT).
  - Timbre output -> 8kHz μ-law -> Twilio.
  - Barge-in: Twilio `clear` event on user interruption.

---

## 9. Data Model (PostgreSQL / Supabase)
- **campaigns:** `id`, `name`, `product_id`, `goal`, `max_concurrent`, `window_start`, `window_end`, `retry_limit`, `status`, `created_at`
- **products:** `id`, `name`, `description`, `price`, `url`, `details` (JSON)
- **contacts:** `id`, `campaign_id`, `name`, `phone`, `email`, `language`, `status` (`new`, `dialing`, `done`, `dnc`), `attempts`, `last_attempt_at`
- **calls:** `id`, `contact_id`, `campaign_id`, `twilio_sid`, `status`, `started_at`, `ended_at`, `duration_sec`, `outcome`, `summary`, `transcript` (JSON), `language_detected`
- **orders:** `id`, `contact_id`, `call_id`, `product_id`, `quantity`, `status` (`awaiting_details`, `details_received`, `paid`, `cod`, `cancelled`), `form_token`, `form_expires_at`, `address`, `pincode`, `created_at`
- **callbacks:** `id`, `contact_id`, `source_call_id`, `due_at`, `reason`, `status`, `created_at`
- **messages:** `id`, `contact_id`, `channel` (`email`, `whatsapp`), `direction`, `body`, `status`, `created_at`

*All timestamps stored in UTC and displayed in IST.*

---

## 10. API Surface
- `POST /campaigns` - Create campaign
- `POST /campaigns/{id}/contacts/import` - Upload CSV of contacts
- `POST /campaigns/{id}/start, /pause, /stop` - Control campaign
- `GET /campaigns/{id}/stats` - Funnel and counters
- `GET /calls, GET /calls/{id}` - List calls, fetch transcript and summary
- `GET /orders, GET /callbacks` - Lists for dashboard
- `POST /twilio/voice` - Returns TwiML to start Media Stream
- `WS /twilio/media` - Bidirectional audio stream
- `POST /twilio/status` - Call status callbacks
- `POST /twilio/whatsapp` - Inbound WhatsApp messages
- `GET /order-form/{token}` & `POST /order-form/{token}` - Public order details form

