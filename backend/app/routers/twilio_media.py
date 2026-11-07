import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Response, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models import Call, Contact, Campaign, Product, Order, Callback, Message
from app.services.audio_converter import AudioConverter
from app.services.gnani_stt import GnaniPrismaSTT
from app.services.gnani_tts import GnaniTimbreTTS
from app.services.llm_agent import VoiceAgentLLM
from app.services.order_service import OrderService
from app.services.twilio_service import TwilioService
from app.services.dispatcher import dispatcher

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/twilio", tags=["Twilio Voice & Media"])
twilio_service = TwilioService()
tts_service = GnaniTimbreTTS()

# Voice entrypoint is served directly at @app.post("/twilio/voice") in main.py

@router.post("/status")
async def twilio_status_callback(request: Request):
    """
    Tracks call status callbacks (initiated, ringing, answered, completed, busy, no-answer).
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    call_status = form_data.get("CallStatus")
    duration = form_data.get("CallDuration")
    call_id = request.query_params.get("call_id")

    logger.info(f"Twilio status callback: CallSid={call_sid}, Status={call_status}, Duration={duration}")

    async with AsyncSessionLocal() as session:
        call = None
        if call_id:
            res = await session.execute(select(Call).where(Call.id == call_id))
            call = res.scalars().first()
        elif call_sid:
            res = await session.execute(select(Call).where(Call.twilio_sid == call_sid))
            call = res.scalars().first()

        if call:
            if call_status == "completed":
                call.status = "completed"
                if duration:
                    call.duration_sec = int(duration)
                call.ended_at = datetime.now(timezone.utc)
            elif call_status in ["busy", "no-answer", "failed"]:
                call.status = call_status
                call.outcome = "no_answer"
                call.ended_at = datetime.now(timezone.utc)
            await session.commit()

            # Free dispatcher slot
            dispatcher.on_call_completed(call.campaign_id, call.id)

    return {"status": "ok"}

@router.websocket("/media")
async def twilio_media_websocket(websocket: WebSocket):
    """
    Bidirectional WebSocket stream exchanging real-time audio with Twilio Programmable Voice.
    Twilio Media Stream sends 8 kHz μ-law -> converted to 8 kHz PCM for Gnani Prisma STT.
    Gnani Timbre TTS audio -> converted to 8 kHz μ-law -> sent to Twilio Media Stream.
    """
    await websocket.accept()
    logger.info("Twilio Media Stream WebSocket connected.")

    stream_sid: Optional[str] = None
    call_id: Optional[str] = None
    contact_id: Optional[str] = None
    campaign_id: Optional[str] = None
    agent: Optional[VoiceAgentLLM] = None
    stt: Optional[GnaniPrismaSTT] = None
    is_agent_speaking = False

    async def handle_agent_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Executes LLM tool calls against the database."""
        logger.info(f"Executing tool {tool_name} with args: {args}")
        async with AsyncSessionLocal() as session:
            if tool_name == "confirm_order":
                await OrderService.create_order_from_call(
                    contact_id=contact_id,
                    call_id=call_id,
                    product_id="curated-linen-kurta-01",
                    quantity=args.get("quantity", 1),
                    email=args.get("email", "customer@example.com"),
                    db=session
                )
                return {"status": "success", "message": "Order created and email sent"}

            elif tool_name == "schedule_callback":
                due_at_str = args.get("due_at_iso")
                try:
                    due_at = datetime.fromisoformat(due_at_str.replace("Z", "+00:00"))
                except Exception:
                    due_at = datetime.now(timezone.utc) + timedelta(hours=2)
                
                cb = Callback(
                    contact_id=contact_id,
                    source_call_id=call_id,
                    due_at=due_at,
                    reason=args.get("reason", "Customer requested callback in 2 hours"),
                    status="pending"
                )
                session.add(cb)
                await session.commit()
                logger.info(f"Callback registered in DB for {due_at} (contact_id={contact_id})")
                return {"status": "success", "message": "Callback scheduled"}

            elif tool_name in ["send_whatsapp_catalog", "send_whatsapp"]:
                phone = args.get("phone") or (contact.phone if contact else "")
                catalog_body = (
                    "🌟 *CURATED India - New Drop Collection*\n\n"
                    "Explore our pure organic minimalist linen kurtas starting at ₹1,499:\n"
                    "👉 https://curatedindia.vercel.app/catalog\n\n"
                    "Complimentary express shipping across India & Cash on Delivery available!"
                )
                twilio_service.send_whatsapp(to_phone=phone, body=catalog_body)
                msg = Message(
                    contact_id=contact_id,
                    channel="whatsapp",
                    direction="outbound",
                    body=catalog_body,
                    status="sent"
                )
                session.add(msg)
                await session.commit()
                logger.info(f"WhatsApp catalog dispatched to {phone}")
                return {"status": "success", "message": "WhatsApp catalog sent"}

            return {"status": "unknown_tool"}

    async def on_stt_transcript(transcript: str, is_final: bool, detected_lang: Optional[str]):
        """Callback fired when Gnani Prisma STT produces user speech."""
        nonlocal is_agent_speaking
        if not transcript or not transcript.strip():
            return

        logger.info(f"Prisma STT (final={is_final}): '{transcript}'")

        # Barge-in support: If agent is speaking, cancel ongoing agent audio
        if is_agent_speaking and stream_sid:
            logger.info("Barge-in detected! Stopping agent audio.")
            clear_event = AudioConverter.create_clear_event(stream_sid)
            await websocket.send_text(json.dumps(clear_event))
            is_agent_speaking = False

        if is_final and agent:
            # LLM generates conversational response
            llm_result = await agent.generate_response(transcript)
            reply_text = llm_result.get("text", "")

            frames = []
            if reply_text and stream_sid:
                is_agent_speaking = True
                # Synthesize with Gnani Timbre TTS (Voice: Shubham)
                audio_ulaw = await tts_service.synthesize(reply_text, voice="Shubham")
                frames = AudioConverter.chunk_ulaw(audio_ulaw, frame_ms=20)

                for frame in frames:
                    if not is_agent_speaking:
                        break # interrupted by barge-in
                    payload_b64 = AudioConverter.bytes_to_base64(frame)
                    event = AudioConverter.create_media_event(stream_sid, payload_b64)
                    await websocket.send_text(json.dumps(event))

                is_agent_speaking = False

            if llm_result.get("call_ended"):
                logger.info("Agent concluded call. Waiting for audio playback to finish before closing stream.")
                playback_wait = max(2.0, (len(frames) * 0.02) + 1.2)
                await asyncio.sleep(playback_wait)
                try:
                    await websocket.close()
                except Exception:
                    pass

    try:
        while True:
            raw_msg = await websocket.receive_text()
            data = json.loads(raw_msg)
            event_type = data.get("event")

            if event_type == "start":
                start_data = data.get("start", {})
                stream_sid = start_data.get("streamSid")
                call_sid = start_data.get("callSid")
                custom_params = start_data.get("customParameters", {})
                call_id = custom_params.get("callId")
                contact_id = custom_params.get("contactId")
                campaign_id = custom_params.get("campaignId")

                if not call_id:
                    import uuid
                    call_id = str(uuid.uuid4())

                logger.info(f"Twilio stream started: streamSid={stream_sid}, callId={call_id}, callSid={call_sid}")

                # Load contact & product info from DB
                async with AsyncSessionLocal() as session:
                    contact = None
                    product = None
                    campaign = None

                    if contact_id:
                        c_res = await session.execute(select(Contact).where(Contact.id == contact_id))
                        contact = c_res.scalars().first()
                    if campaign_id:
                        camp_res = await session.execute(select(Campaign).where(Campaign.id == campaign_id))
                        campaign = camp_res.scalars().first()
                    if campaign and campaign.product_id:
                        p_res = await session.execute(select(Product).where(Product.id == campaign.product_id))
                        product = p_res.scalars().first()
                    if not product:
                        p_all = await session.execute(select(Product))
                        product = p_all.scalars().first()

                    # Fallback contact if none provided
                    if not contact:
                        contact = Contact(
                            campaign_id=campaign.id if campaign else "default-camp",
                            name="Tanmay",
                            phone=start_data.get("from") or start_data.get("to") or "",
                            language="hinglish",
                            status="dialing"
                        )
                        session.add(contact)
                        await session.commit()
                        await session.refresh(contact)
                        contact_id = contact.id

                    # Ensure Call row exists in database
                    call_check = await session.execute(select(Call).where(Call.id == call_id))
                    call_row = call_check.scalars().first()
                    if not call_row:
                        call_row = Call(
                            id=call_id,
                            contact_id=contact.id,
                            campaign_id=campaign.id if campaign else (campaign_id or "default-camp"),
                            twilio_sid=call_sid,
                            status="in-progress",
                            started_at=datetime.now(timezone.utc)
                        )
                        session.add(call_row)
                        await session.commit()

                    # Initialize STT and Agent
                    stt = GnaniPrismaSTT(on_transcript=on_stt_transcript)
                    await stt.connect()

                    agent = VoiceAgentLLM(
                        contact_name=contact.name if contact else "Tanmay",
                        contact_phone=contact.phone if contact else "",
                        contact_email=contact.email if contact else None,
                        preferred_language=contact.language if contact else "hinglish",
                        product_info=product.details if product else {},
                        campaign_goal=campaign.goal if campaign else "Share new drop details and send WhatsApp catalog",
                        previous_call_context=contact.notes if contact else None,
                        tool_handler=handle_agent_tool
                    )

                    # Trigger Opening Line: The moment WebSocket connects, backend sends "Hi, kya mai Tanmay se baat kar raha hoon?"
                    greeting_text = agent.get_initial_greeting()
                    logger.info(f"Triggering opening line for Shubham: '{greeting_text}'")
                    agent.history.append({
                        "speaker": "agent",
                        "text": greeting_text,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })

                    audio_ulaw = await tts_service.synthesize(greeting_text, voice="Shubham")
                    frames = AudioConverter.chunk_ulaw(audio_ulaw, frame_ms=20)
                    for frame in frames:
                        payload_b64 = AudioConverter.bytes_to_base64(frame)
                        await websocket.send_text(json.dumps(AudioConverter.create_media_event(stream_sid, payload_b64)))

            elif event_type == "media":
                media_payload = data.get("media", {}).get("payload", "")
                if media_payload and stt and stt.is_connected:
                    ulaw_bytes = AudioConverter.base64_to_bytes(media_payload)
                    pcm_bytes = AudioConverter.ulaw_to_pcm16(ulaw_bytes)
                    await stt.send_audio(pcm_bytes)

            elif event_type == "stop":
                logger.info(f"Twilio stream stopped for callId={call_id}")
                break

    except WebSocketDisconnect:
        logger.info(f"Twilio WebSocket disconnected for callId={call_id}")
    except Exception as e:
        logger.error(f"Error in Twilio Media WebSocket: {e}", exc_info=True)
    finally:
        if stt:
            await stt.close()

        # Finalize Call record in database
        if call_id and agent:
            summary_info = agent.generate_summary()
            async with AsyncSessionLocal() as session:
                res = await session.execute(select(Call).where(Call.id == call_id))
                call = res.scalars().first()
                if call:
                    call.status = "completed"
                    call.ended_at = datetime.now(timezone.utc)
                    call.duration_sec = summary_info.get("duration_sec", 15)
                    call.outcome = summary_info.get("outcome")
                    call.summary = summary_info.get("summary")
                    call.transcript = agent.history
                    await session.commit()

                # Mark contact status as done if not dnc
                if contact_id:
                    c_res = await session.execute(select(Contact).where(Contact.id == contact_id))
                    c = c_res.scalars().first()
                    if c and c.status != "dnc":
                        c.status = "done"
                        await session.commit()

            if campaign_id:
                dispatcher.on_call_completed(campaign_id, call_id)

