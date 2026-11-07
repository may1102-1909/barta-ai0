import logging
from typing import Optional
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from app.config import settings

logger = logging.getLogger(__name__)

class TwilioService:
    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.api_key_sid = settings.TWILIO_API_KEY_SID
        self.api_key_secret = settings.TWILIO_API_KEY_SECRET
        self.phone_number = settings.TWILIO_PHONE_NUMBER
        self.client = None

        if self.api_key_sid and self.api_key_secret and self.account_sid:
            try:
                self.client = Client(self.api_key_sid, self.api_key_secret, self.account_sid)
                logger.info("Initialized Twilio Client using API Key SID & Secret.")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client with API Key: {e}")
        elif self.account_sid and self.auth_token:
            try:
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("Initialized Twilio Client using Account SID & Auth Token.")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")

    def generate_twiml(self, call_id: Optional[str] = None, contact_id: Optional[str] = None, campaign_id: Optional[str] = None) -> str:
        """
        Generates TwiML connecting the call directly to our bidirectional 
        WebSocket Media Stream endpoint (/twilio/media).
        """
        response = VoiceResponse()
        connect = Connect()
        
        # Build WebSocket URL from configured base URL
        ws_base = settings.TWILIO_WEBHOOK_URL.replace("https://", "wss://").replace("http://", "ws://").rstrip("/")
        stream_url = f"{ws_base}/twilio/media"
        
        stream = Stream(url=stream_url)
        if call_id:
            stream.parameter(name="callId", value=call_id)
        if contact_id:
            stream.parameter(name="contactId", value=contact_id)
        if campaign_id:
            stream.parameter(name="campaignId", value=campaign_id)
        
        connect.append(stream)
        response.append(connect)
        return str(response)

    async def place_call(
        self,
        to_phone: str,
        call_id: str,
        contact_id: str,
        campaign_id: str
    ) -> Optional[str]:
        """
        Initiates outbound phone call via Twilio Programmable Voice.
        Returns Twilio Call SID if successful.
        """
        if not self.client or not self.phone_number:
            logger.info(f"[SIMULATED CALL] Dialing {to_phone} for call_id={call_id}")
            return f"SIM_CA_{call_id[:12]}"

        try:
            # Twilio will fetch the TwiML from /twilio/voice
            voice_url = f"{settings.TWILIO_WEBHOOK_URL}/twilio/voice?call_id={call_id}&contact_id={contact_id}&campaign_id={campaign_id}"
            status_callback_url = f"{settings.TWILIO_WEBHOOK_URL}/twilio/status?call_id={call_id}"

            call = self.client.calls.create(
                to=to_phone,
                from_=self.phone_number,
                url=voice_url,
                status_callback=status_callback_url,
                status_callback_event=["initiated", "ringing", "answered", "completed"],
                status_callback_method="POST"
            )
            logger.info(f"Twilio call initiated: SID={call.sid} to {to_phone}")
            return call.sid
        except Exception as e:
            logger.error(f"Twilio call creation failed for {to_phone}: {e}")
            return None

    def send_whatsapp(self, to_phone: str, body: str) -> bool:
        """Sends WhatsApp message using Twilio WhatsApp API or logs as fallback."""
        if not self.client:
            logger.warning("Twilio client not initialized. Cannot dispatch WhatsApp.")
            return False

        try:
            from_wa = settings.TWILIO_WHATSAPP_NUMBER or "whatsapp:+14155238886"
            to_wa = to_phone if to_phone.startswith("whatsapp:") else f"whatsapp:{to_phone}"
            msg = self.client.messages.create(
                from_=from_wa,
                to=to_wa,
                body=body
            )
            logger.info(f"Twilio WhatsApp sent successfully: SID={msg.sid} to {to_wa}")
            return True
        except Exception as e:
            logger.warning(f"Twilio WhatsApp dispatch notice (recipient may need to join Twilio sandbox): {e}")
            # Attempt SMS dispatch if WhatsApp requires sandbox opt-in
            try:
                raw_phone = to_phone.replace("whatsapp:", "")
                sms = self.client.messages.create(
                    from_=self.phone_number,
                    to=raw_phone,
                    body=body
                )
                logger.info(f"Dispatched via fallback SMS: SID={sms.sid} to {raw_phone}")
                return True
            except Exception as ex_sms:
                logger.warning(f"Fallback SMS notice: {ex_sms}")
                return False

