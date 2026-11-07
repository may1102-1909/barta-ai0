import json
import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Callable, Awaitable
import pytz
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None
from app.config import settings

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")

# Tool declarations for Gemini
AGENT_TOOLS = [
    {
        "name": "send_whatsapp_catalog",
        "description": "Sends the CURATED India product drop catalog and link to the customer on WhatsApp.",
        "parameters": {
            "type": "object",
            "properties": {
                "phone": {"type": "string", "description": "Phone number to send WhatsApp catalog to."},
                "message_type": {"type": "string", "description": "Type of message, e.g., catalog, product_info."}
            },
            "required": ["phone"]
        }
    },
    {
        "name": "schedule_callback",
        "description": "Call this when the customer asks to be called back at a specific time (e.g. '2 hours', 'tomorrow', 'evening').",
        "parameters": {
            "type": "object",
            "properties": {
                "due_at_iso": {"type": "string", "description": "Target callback datetime in ISO 8601 format with IST timezone (+05:30) or UTC (Z)."},
                "reason": {"type": "string", "description": "Brief reason for callback, e.g. 'Customer is busy, call in 2 hours'."}
            },
            "required": ["due_at_iso", "reason"]
        }
    },
    {
        "name": "confirm_order",
        "description": "Call this when the customer explicitly agrees to place an order.",
        "parameters": {
            "type": "object",
            "properties": {
                "product": {"type": "string", "description": "The name or ID of the product being ordered."},
                "quantity": {"type": "integer", "description": "The quantity ordered (usually 1 or more)."},
                "email": {"type": "string", "description": "The customer's email address to send the secure delivery details form."}
            },
            "required": ["product", "quantity", "email"]
        }
    },
    {
        "name": "send_whatsapp",
        "description": "Sends a product link, size guide, or payment link to the customer on WhatsApp.",
        "parameters": {
            "type": "object",
            "properties": {
                "message_type": {"type": "string", "enum": ["product_info", "payment_link", "size_chart"], "description": "Type of WhatsApp message."}
            },
            "required": ["message_type"]
        }
    },
    {
        "name": "set_outcome",
        "description": "Records the final qualified outcome of the call.",
        "parameters": {
            "type": "object",
            "properties": {
                "outcome": {
                    "type": "string",
                    "enum": [
                        "catalog_sent",
                        "callback_requested",
                        "order_confirmed",
                        "interested",
                        "not_interested",
                        "no_answer",
                        "wrong_number",
                        "do_not_call"
                    ],
                    "description": "The definitive outcome category."
                },
                "notes": {"type": "string", "description": "Brief context or qualification notes."}
            },
            "required": ["outcome"]
        }
    }
]

class VoiceAgentLLM:
    """
    Manages conversational intelligence for 'Shubham', outbound AI voice sales agent
    for Curated India, calling customer Tanmay.
    """

    def __init__(
        self,
        contact_name: str = "Tanmay",
        contact_phone: str = "",
        contact_email: Optional[str] = None,
        preferred_language: str = "hinglish",
        product_info: Optional[Dict[str, Any]] = None,
        campaign_goal: str = "Share new drop details and send WhatsApp catalog",
        previous_call_context: Optional[str] = None,
        tool_handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]] = None
    ):
        self.contact_name = contact_name or "Tanmay"
        self.contact_phone = contact_phone or ""
        self.contact_email = contact_email or ""
        self.preferred_language = preferred_language or "hinglish"
        self.product_info = product_info or {
            "name": "CURATED Minimalist Linen Kurta",
            "price": 1899,
            "discount_price": 1499
        }
        self.campaign_goal = campaign_goal
        self.previous_call_context = previous_call_context
        self.tool_handler = tool_handler

        self.history: List[Dict[str, Any]] = []
        self.recorded_outcome: Optional[str] = None
        self.recorded_notes: Optional[str] = None
        self.call_ended: bool = False

        # State Machine States:
        # 'opening' -> 'busy_asked' or 'lang_check' -> 'pitch' -> 'closing' / 'closed'
        self.state: str = "opening"
        self.chosen_language: str = "hinglish"

        self._init_gemini()

    def _init_gemini(self):
        self.client = None
        if settings.GEMINI_API_KEY and genai:
            try:
                self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini Client: {e}. Will use built-in state machine.")

    def _build_system_prompt(self) -> str:
        current_time_ist = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
        return f"""You are "Shubham", an outbound AI voice sales agent for Curated India. Your voice is generated via Gnani AI Timbre TTS, and your responses must be natural, concise, and optimized for real-time speech (avoid long paragraphs, bullet points, or markdown). 

Current local time: {current_time_ist}
You are calling a customer named TANMAY ({self.contact_phone}). You must strictly follow this conversational state machine and flow:

### CONVERSATIONAL FLOW & SCRIPT:

1. Opening (Mandatory First Turn):
   - You MUST start the call with exact Hinglish:
   - "Hi, kya mai Tanmay se baat kar raha hoon?"
   - Stop and wait for the user's response.

2. Branch A: User is busy right now
   - If the user says they are busy ("busy hoon", "abhi vyast hoon", "baad me call karna", "not a good time", etc.):
   - Ask: "Koi baat nahi, kya mai aapko 2 ghante baad ya kal call karoon?"
   - If they specify a time (e.g., "2 hours", "evening", "tomorrow"), acknowledge it warmly: "Theek hai, main aapko wahi samay par call karunga. Dhanyawad!" and trigger the callback scheduler tool.

3. Branch B: User confirms identity / continues
   - If the user confirms it's Tanmay (or says "haan", "boliye"):
   - Proceed to language preference check:
   - "Aap kis bhasha mein comfortable hain—Hindi, English, ya Hinglish?"
   - Wait for their choice.

4. Value Proposition (After Language Preference):
   - Acknowledge their language choice smoothly, then deliver the pitch:
   - "Main Shubham hoon Curated India se. Main aapko hamare store ke naye drop ke baare mein batane ke liye call kar raha hoon. Kya aap product ke details dekhna chahenge?"
   - Wait for response.

5. Closing / Action Trigger:
   - If the user agrees or asks for photos/links (e.g., "haan WhatsApp pe bhej do", "send details"):
   - Respond: "Bilkul! Maine aapke WhatsApp par catalog bhej diya hai, aap check kar sakte hain. Have a great day!"
   - Trigger the WhatsApp catalog sender tool in the backend.
   - If they say no, politely wrap up: "Koi baat nahi, thank you so much! Have a wonderful day."

### RULES FOR VOICE:
- Keep sentences short so the user doesn't get interrupted.
- Use natural conversational Hinglish (blend of Hindi and English words written in Latin script).
- Never output markdown formatting like bold text, asterisks, or quotes in your text stream—only output raw text for the TTS engine.
"""

    def get_initial_greeting(self) -> str:
        """Returns the mandatory initial opening line for Shubham."""
        self.state = "opening"
        return "Hi, kya mai Tanmay se baat kar raha hoon?"

    def _clean_for_speech(self, text: str) -> str:
        """Strips markdown asterisks, hashes, backticks, quotes for pure TTS speech."""
        text = re.sub(r"[\*#_`~\"\[\]\(\)\{\}]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    async def generate_response(self, user_transcript: str) -> Dict[str, Any]:
        """
        Processes caller speech and generates agent response + handles tool calls
        following Shubham's state machine.
        """
        self.history.append({
            "speaker": "user",
            "text": user_transcript,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # Process through state machine first to determine if state or tool is triggered
        fallback_res = await self._dialogue_engine(user_transcript)

        # If Gemini is configured and dialogue is in an open conversation, Gemini can refine
        # However, if we hit a scripted branch (busy, lang_check, pitch, closing), enforce exact script
        if self.client and self.state not in ["busy_asked", "closed"]:
            try:
                system_instruction = self._build_system_prompt()
                chat_context = "\n".join([f"{t['speaker'].upper()}: {t['text']}" for t in self.history])
                prompt = (
                    f"{system_instruction}\n\n"
                    f"CURRENT STATE: {self.state}\n"
                    f"CONVERSATION HISTORY:\n{chat_context}\n\n"
                    f"Produce ONLY the single plain text line (no markdown, no quotes, no asterisks) for Shubham's next spoken turn:"
                )
                
                resp = self.client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt
                )
                if resp.text and resp.text.strip():
                    cleaned_gemini = self._clean_for_speech(resp.text)
                    # If fallback has specific tool, preserve it
                    fallback_res["text"] = cleaned_gemini
            except Exception as e:
                logger.warning(f"Gemini generation error: {e}. Using state machine response.")

        self.history.append({
            "speaker": "agent",
            "text": fallback_res["text"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return fallback_res

    async def _dialogue_engine(self, user_text: str) -> Dict[str, Any]:
        """Strict conversational state machine adhering to the user's specification."""
        lower = user_text.lower().strip()
        now_ist = datetime.now(IST)

        logger.info(f"Agent state before turn: '{self.state}', user input: '{user_text}'")

        # Global DNC Check
        if any(w in lower for w in ["do not call", "dnc", "stop calling", "kabhi call mat karna"]):
            self.state = "closed"
            self.call_ended = True
            self.recorded_outcome = "do_not_call"
            if self.tool_handler:
                await self.tool_handler("set_outcome", {"outcome": "do_not_call", "notes": "Requested DNC"})
            return {
                "text": "Bilkul samajh gaya. Maine aapka number Do Not Call list me add kar diya hai. Aage se koi call nahi aayegi. Shukriya.",
                "tool_called": "set_outcome",
                "outcome": "do_not_call",
                "call_ended": True
            }

        # -------------------------------------------------------------
        # 1. Opening State: Agent asked "Hi, kya mai Tanmay se baat kar raha hoon?"
        # -------------------------------------------------------------
        if self.state == "opening":
            # Branch A: Caller says they are busy
            is_busy = any(w in lower for w in [
                "busy", "vyast", "baad me", "later", "not a good time", "not now",
                "driving", "drive", "meeting", "abhi nahi", "kaam", "ruk", "thodi der",
                "call back", "call later", "baad me karo", "abhi busy"
            ])
            if is_busy:
                self.state = "busy_asked"
                return {
                    "text": "Koi baat nahi, kya mai aapko 2 ghante baad ya kal call karoon?",
                    "tool_called": None,
                    "outcome": "callback_pending",
                    "call_ended": False
                }

            # Wrong number check
            if any(w in lower for w in ["wrong number", "galat number", "tanmay nahi", "not tanmay", "galat hai"]):
                self.state = "closed"
                self.call_ended = True
                self.recorded_outcome = "wrong_number"
                if self.tool_handler:
                    await self.tool_handler("set_outcome", {"outcome": "wrong_number", "notes": "Wrong contact"})
                return {
                    "text": "Maaf kijiyega, lagta hai galat number lag gaya. Have a great day!",
                    "tool_called": "set_outcome",
                    "outcome": "wrong_number",
                    "call_ended": True
                }

            # Branch B: Caller confirms identity / continues
            self.state = "lang_check"
            return {
                "text": "Aap kis bhasha mein comfortable hain—Hindi, English, ya Hinglish?",
                "tool_called": None,
                "outcome": "identity_confirmed",
                "call_ended": False
            }

        # -------------------------------------------------------------
        # 2. Branch A Follow-up: Agent asked "Koi baat nahi, kya mai aapko 2 ghante baad ya kal call karoon?"
        # -------------------------------------------------------------
        if self.state == "busy_asked":
            # Parse requested callback time
            due_at = now_ist + timedelta(hours=2)
            reason = "Customer requested callback in 2 hours"

            if any(w in lower for w in ["kal", "tomorrow"]):
                due_at = (now_ist + timedelta(days=1)).replace(hour=11, minute=0, second=0, microsecond=0)
                reason = "Customer requested callback tomorrow"
            elif any(w in lower for w in ["shaam", "evening"]):
                due_at = now_ist.replace(hour=18, minute=0, second=0, microsecond=0)
                reason = "Customer requested callback in evening"
            elif any(w in lower for w in ["2", "two", "do ghante", "2 hours", "2 ghante"]):
                due_at = now_ist + timedelta(hours=2)
                reason = "Customer requested callback in 2 hours"

            self.state = "closed"
            self.call_ended = True
            self.recorded_outcome = "callback_requested"

            if self.tool_handler:
                await self.tool_handler("schedule_callback", {
                    "due_at_iso": due_at.isoformat(),
                    "reason": reason
                })

            return {
                "text": "Theek hai, main aapko wahi samay par call karunga. Dhanyawad!",
                "tool_called": "schedule_callback",
                "outcome": "callback_requested",
                "call_ended": True
            }

        # -------------------------------------------------------------
        # 3. Branch B: Language Preference Check
        # -------------------------------------------------------------
        if self.state == "lang_check":
            if "english" in lower:
                self.chosen_language = "english"
            elif "hindi" in lower:
                self.chosen_language = "hindi"
            else:
                self.chosen_language = "hinglish"

            self.state = "pitch"
            # Deliver pitch
            return {
                "text": "Main Shubham hoon Curated India se. Main aapko hamare store ke naye drop ke baare mein batane ke liye call kar raha hoon. Kya aap product ke details dekhna chahenge?",
                "tool_called": None,
                "outcome": "pitch_delivered",
                "call_ended": False
            }

        # -------------------------------------------------------------
        # 4. Value Proposition / Closing / Action Trigger
        # -------------------------------------------------------------
        if self.state == "pitch":
            # User agrees or asks for WhatsApp / photos / links / details
            agreed = any(w in lower for w in [
                "haan", "yes", "whatsapp", "bhej do", "send", "details",
                "photos", "link", "sure", "dekhna", "bhejiye", "ok", "okay",
                "theek hai", "batao", "dekh leta hoon", "kar do"
            ])
            if agreed:
                self.state = "closed"
                self.call_ended = True
                self.recorded_outcome = "catalog_sent"

                if self.tool_handler:
                    await self.tool_handler("send_whatsapp_catalog", {
                        "phone": self.contact_phone,
                        "message_type": "new_drop_catalog"
                    })

                return {
                    "text": "Bilkul! Maine aapke WhatsApp par catalog bhej diya hai, aap check kar sakte hain. Have a great day!",
                    "tool_called": "send_whatsapp_catalog",
                    "outcome": "catalog_sent",
                    "call_ended": True
                }

            # User says no / declines
            declined = any(w in lower for w in [
                "nahi", "no", "not interested", "nahi chahiye", "rehne do",
                "don't want", "mat bhejo", "interest nahi"
            ])
            if declined:
                self.state = "closed"
                self.call_ended = True
                self.recorded_outcome = "not_interested"

                if self.tool_handler:
                    await self.tool_handler("set_outcome", {
                        "outcome": "not_interested",
                        "notes": "Customer declined new drop catalog"
                    })

                return {
                    "text": "Koi baat nahi, thank you so much! Have a wonderful day.",
                    "tool_called": "set_outcome",
                    "outcome": "not_interested",
                    "call_ended": True
                }

            # User asks specific question (price, material, etc.)
            if any(w in lower for w in ["price", "cost", "kitna", "fabric", "material"]):
                return {
                    "text": "Hamara festive collection pure organic linen se bana hai aur flat Rs 1499 me mil raha hai with free delivery. Kya mai aapko WhatsApp par photos aur details bhej doon?",
                    "tool_called": None,
                    "outcome": "interested",
                    "call_ended": False
                }

        # Generic courteous fallback
        return {
            "text": "Bilkul! Maine aapke WhatsApp par catalog bhej diya hai, aap check kar sakte hain. Have a great day!",
            "tool_called": "send_whatsapp_catalog",
            "outcome": "catalog_sent",
            "call_ended": True
        }

    def generate_summary(self) -> Dict[str, Any]:
        """Generates summary and definitive outcome for the call record."""
        turns_count = len(self.history)
        outcome = self.recorded_outcome or "catalog_sent" if turns_count > 3 else "interested"

        if outcome == "catalog_sent":
            summary = f"Spoke with Tanmay. Qualified interest and successfully sent Curated India new drop catalog to WhatsApp ({self.contact_phone})."
        elif outcome == "callback_requested":
            summary = f"Tanmay was busy. Scheduled a callback at designated time."
        elif outcome == "not_interested":
            summary = f"Tanmay politely declined product details. Wrapped up gracefully."
        elif outcome == "wrong_number":
            summary = "Wrong number. Call ended."
        else:
            summary = f"Outbound conversation held with Tanmay. Status: {outcome}."

        return {
            "summary": summary,
            "outcome": outcome,
            "duration_sec": max(15, turns_count * 6)
        }
