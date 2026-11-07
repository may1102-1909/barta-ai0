import io
import csv
import re
import logging
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db
from app.models import Campaign, Contact, Call, Product, Order
from app.services.dispatcher import dispatcher

logger = logging.getLogger(__name__)

try:
    from google import genai
except ImportError:
    genai = None

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

DEFAULT_SCRIPTS = {
    "hinglish": (
        "{\n"
        "  \"platform\": \"BARTA ai\",\n"
        "  \"brand\": \"Curated India\",\n"
        "  \"agent\": \"Shubham\",\n"
        "  \"customer\": \"Tanmay\",\n"
        "  \"state_machine\": {\n"
        "    \"1_opening\": {\n"
        "      \"speaker\": \"agent\",\n"
        "      \"text\": \"Hi, kya mai Tanmay se baat kar raha hoon?\",\n"
        "      \"branches\": {\n"
        "        \"busy\": \"2_branch_a_busy\",\n"
        "        \"confirmed\": \"3_branch_b_language\"\n"
        "      }\n"
        "    },\n"
        "    \"2_branch_a_busy\": {\n"
        "      \"user\": \"Main abhi busy hoon / Not a good time.\",\n"
        "      \"agent\": \"Koi baat nahi, kya mai aapko 2 ghante baad ya kal call karoon?\",\n"
        "      \"if_2_hours\": {\n"
        "        \"agent\": \"Theek hai, 2 ghante baad call karunga.\",\n"
        "        \"action\": \"schedule_callback(2_hours)\"\n"
        "      }\n"
        "    },\n"
        "    \"3_branch_b_language\": {\n"
        "      \"user\": \"Haan, boliye.\",\n"
        "      \"agent\": \"Aap kis bhasha mein comfortable hain—Hindi, English, ya Hinglish?\",\n"
        "      \"next\": \"4_pitch\"\n"
        "    },\n"
        "    \"4_pitch\": {\n"
        "      \"agent\": \"Main Shubham hoon Curated India se. Main aapko hamare store ke naye drop ke baare mein batane ke liye call kar raha hoon. Kya aap product ke details dekhna chahenge?\",\n"
        "      \"transitions\": {\n"
        "        \"interested_whatsapp_or_email\": \"5_closing\"\n"
        "      }\n"
        "    },\n"
        "    \"5_closing\": {\n"
        "      \"user\": \"Haan WhatsApp/email pe bhej do.\",\n"
        "      \"agent\": \"Bilkul! Maine aapke WhatsApp aur email par secure order link aur catalog share kar diya hai. Thank you so much, have a great day!\",\n"
        "      \"action\": \"send_secure_link_and_catalog\"\n"
        "    }\n"
        "  }\n"
        "}"
    ),
    "hindi": (
        "[नमस्ते और परिचय]\n"
        "एजेंट: \"नमस्ते! क्या मेरी बात ग्राहक महोदय से हो रही है?\"\n"
        "ग्राहक: \"हाँ, बोलिए।\"\n"
        "एजेंट: \"नमस्ते! मैं CURATED India की तरफ से बात कर रहा हूँ। आज मैं आपको हमारे नए फेस्टिव कलेक्शन के बारे में जानकारी देने के लिए संपर्क कर रहा हूँ। क्या आपके पास 2 मिनट का समय होगा?\"\n\n"
        "[उत्पाद और विशेष छूट]\n"
        "एजेंट: \"धन्यवाद! हमारे नए 100% प्योर ऑर्गेनिक लिनेन कुर्ते लॉन्च हो चुके हैं, जो बेहद आरामदायक और प्रीमियम क्वालिटी के हैं। इस त्यौहार के अवसर पर आपको फ्लैट ₹1,499 में फ्री डिलीवरी और 7 दिनों की आसान रिटर्न सुविधा के साथ मिल रहा है।\"\n\n"
        "[संवाद व सहायता]\n"
        "ग्राहक व्यस्त होने पर: \"कोई समस्या नहीं! क्या मैं आपको 2 घंटे बाद या कल कॉल कर सकता हूँ?\"\n"
        "व्हाट्सएप कैटलॉग के लिए: \"बिल्कुल! मैं अभी आपके व्हाट्सएप पर पूरा कलेक्शन और साइज चार्ट भेज रहा हूँ।\"\n\n"
        "[समापन और कॉल टू एक्शन]\n"
        "एजेंट: \"क्या आप अभी ऑर्डर कन्फर्म करना चाहेंगे या व्हाट्सएप पर कैटलॉग देखना पसंद करेंगे? धन्यवाद, आपका दिन शुभ हो!\""
    ),
    "english": (
        "[Introduction & Verification]\n"
        "Agent: \"Hello! Am I speaking with the customer?\"\n"
        "Customer: \"Yes, who is this?\"\n"
        "Agent: \"Hi! This is the outbound representative from CURATED India. I'm reaching out with a quick 2-minute update regarding our newly launched festive collection. Do you have a moment?\"\n\n"
        "[Value Proposition & Offer]\n"
        "Agent: \"Wonderful! We've introduced our 100% handcrafted organic linen kurtas, designed for breathable comfort and modern festivities. While the standard retail price is Rs 1899, our limited festive promotion gives you a flat price of Rs 1499 with free express shipping across India and an easy 7-day exchange guarantee.\"\n\n"
        "[Objection Handling & Nuance]\n"
        "If Customer is Busy: \"No problem at all! Would you prefer a callback in 2 hours or tomorrow morning?\"\n"
        "If Customer wants digital catalog: \"Certainly! I can send the lookbook, high-res photos, and size guide directly to your WhatsApp right away.\"\n\n"
        "[Call-to-Action & Graceful Exit]\n"
        "Agent: \"Would you like me to reserve your size today, or should I ping you the complete catalog on WhatsApp? Thank you so much for your time, and have a wonderful day!\""
    )
}

class ScriptGenerateRequest(BaseModel):
    goal: str
    product_url: Optional[str] = None
    language: str = "hinglish" # "hindi", "english", "hinglish"

class ScriptGenerateResponse(BaseModel):
    script: str
    language: str
    word_count: int

class CampaignCreate(BaseModel):
    name: str
    product_id: Optional[str] = "curated-linen-kurta-01"
    product_url: Optional[str] = None
    goal: str = "Introduce the CURATED Minimalist Linen Kurta festive offer and confirm orders."
    max_concurrent: int = 1
    window_start: str = "00:00"
    window_end: str = "23:59"
    retry_limit: int = 2
    script: Optional[str] = None
    language: Optional[str] = "hinglish"

class CampaignResponse(BaseModel):
    id: str
    name: str
    product_id: str
    product_url: Optional[str] = None
    script: Optional[str] = None
    language: Optional[str] = "hinglish"
    goal: str
    max_concurrent: int
    window_start: str
    window_end: str
    retry_limit: int
    status: str
    created_at: datetime
    total_contacts: int = 0
    total_calls: int = 0
    orders_count: int = 0

@router.get("")
async def list_campaigns(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).order_by(desc(Campaign.created_at)))
    campaigns = result.scalars().all()
    
    output = []
    for camp in campaigns:
        # Count contacts
        c_res = await db.execute(select(func.count(Contact.id)).where(Contact.campaign_id == camp.id))
        total_contacts = c_res.scalar() or 0

        # Count calls
        calls_res = await db.execute(select(func.count(Call.id)).where(Call.campaign_id == camp.id))
        total_calls = calls_res.scalar() or 0

        # Count confirmed orders
        orders_res = await db.execute(
            select(func.count(Order.id))
            .join(Contact, Order.contact_id == Contact.id)
            .where(Contact.campaign_id == camp.id)
        )
        orders_count = orders_res.scalar() or 0

        output.append({
            "id": camp.id,
            "name": camp.name,
            "product_id": camp.product_id,
            "product_url": getattr(camp, "product_url", None),
            "script": getattr(camp, "script", None),
            "language": getattr(camp, "language", "hinglish") or "hinglish",
            "goal": camp.goal,
            "max_concurrent": camp.max_concurrent,
            "window_start": camp.window_start,
            "window_end": camp.window_end,
            "retry_limit": camp.retry_limit,
            "status": camp.status,
            "created_at": camp.created_at.isoformat() if camp.created_at else None,
            "total_contacts": total_contacts,
            "total_calls": total_calls,
            "orders_count": orders_count
        })
    return output

@router.post("/generate-script", response_model=ScriptGenerateResponse)
async def generate_script(payload: ScriptGenerateRequest):
    """
    Generates an authentic ~2-minute outbound call script (under 800 words)
    using Gemini, customized for Goal, Product URL, and Language (Hindi, English, Hinglish).
    """
    lang_key = (payload.language or "hinglish").lower().strip()
    fallback = DEFAULT_SCRIPTS.get(lang_key, DEFAULT_SCRIPTS["hinglish"])

    if not settings.GEMINI_API_KEY or not genai:
        return ScriptGenerateResponse(
            script=fallback,
            language=lang_key,
            word_count=len(fallback.split())
        )

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        if lang_key == "hinglish":
            prompt = (
                "You are an expert scriptwriter for BARTA ai, an outbound voice sales platform. \n"
                "Generate a JSON-structured voice agent script for an e-commerce brand named \"Curated India\" selling a new fashion drop to a customer named Tanmay.\n\n"
                "The script must strictly follow this state machine and dialogue flow:\n"
                "1. Opening line (Hinglish): \"Hi, kya mai Tanmay se baat kar raha hoon?\"\n"
                "2. Branch A (Busy response): If user says they are busy, ask: \"Koi baat nahi, kya mai aapko 2 ghante baad ya kal call karoon?\" If they specify 2 hours, acknowledge it (\"Theek hai, 2 ghante baad call karunga\") and schedule a callback.\n"
                "3. Branch B (Confirmation / continuation): If user confirms identity, ask: \"Aap kis bhasha mein comfortable hain—Hindi, English, ya Hinglish?\"\n"
                "4. Pitch (After language choice): \"Main Shubham hoon Curated India se. Main aapko hamare store ke naye drop ke baare mein batane ke liye call kar raha hoon. Kya aap product ke details dekhna chahenge?\"\n"
                "5. Closing: If user says \"haan WhatsApp/email pe bhej do\", confirm sending the secure link.\n\n"
                "Output the script clearly with conditional branches and speaker turns. Keep sentences short and conversational."
            )
        else:
            lang_instruction = (
                "Natural polite Hindi"
                if lang_key == "hindi"
                else "Professional, warm, clear Indian English"
            )
            prompt = (
                f"You are an expert scriptwriter for BARTA ai, an outbound voice sales platform.\n"
                f"Generate a JSON-structured voice agent script for an e-commerce brand named \"Curated India\" selling a new fashion drop to a customer named Tanmay in {lang_instruction}.\n\n"
                f"The script must strictly follow this state machine and dialogue flow:\n"
                f"1. Opening line: Confirm customer identity politely.\n"
                f"2. Branch A (Busy response): If user says they are busy, ask if you can call back in 2 hours or tomorrow, and schedule callback.\n"
                f"3. Branch B (Confirmation / continuation): Inquire language comfort or proceed directly to pitch.\n"
                f"4. Pitch: Introduce as Shubham from Curated India, share the new fashion drop details and ask if they would like product details.\n"
                f"5. Closing: If user says send to WhatsApp or email, confirm sending the secure link.\n\n"
                f"Output the script clearly with conditional branches and speaker turns. Keep sentences short and conversational."
            )

        resp = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt
        )
        if resp.text and resp.text.strip():
            script_text = resp.text.strip()
            return ScriptGenerateResponse(
                script=script_text,
                language=lang_key,
                word_count=len(script_text.split())
            )
    except Exception as e:
        logger.warning(f"Gemini script generation failed: {e}. Returning tailored default script.")

    return ScriptGenerateResponse(
        script=fallback,
        language=lang_key,
        word_count=len(fallback.split())
    )

@router.post("/parse-script-doc")
async def parse_script_doc(file: UploadFile = File(...)):
    """
    Parses an uploaded Microsoft Word (.docx) document (up to 50MB) and returns
    its extracted script text.
    """
    filename = file.filename or ""
    if not filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only Word document (.docx) files are supported.")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed 50MB limit.")

    try:
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            if "word/document.xml" not in z.namelist():
                raise HTTPException(status_code=400, detail="Invalid .docx file (missing word/document.xml).")
            xml_data = z.read("word/document.xml")
            root = ET.fromstring(xml_data)

            paragraphs = []
            for p in root.iter():
                if p.tag.endswith("}p") or p.tag == "p":
                    text_parts = [t.text for t in p.iter() if (t.tag.endswith("}t") or t.tag == "t") and t.text]
                    para_text = "".join(text_parts).strip()
                    if para_text:
                        paragraphs.append(para_text)

            extracted = "\n\n".join(paragraphs).strip()
            if not extracted:
                raise HTTPException(status_code=400, detail="No readable text found in the uploaded Word document.")

            return {
                "script": extracted,
                "filename": filename,
                "size": len(content),
                "word_count": len(extracted.split())
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error parsing .docx: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to read Word document: {str(e)}")

@router.post("")
async def create_campaign(payload: CampaignCreate, db: AsyncSession = Depends(get_db)):
    # Verify product exists or use default
    prod_res = await db.execute(select(Product).where(Product.id == payload.product_id))
    product = prod_res.scalars().first()
    if not product:
        prod_all = await db.execute(select(Product))
        product = prod_all.scalars().first()

    campaign = Campaign(
        name=payload.name,
        product_id=product.id if product else "default",
        product_url=payload.product_url,
        goal=payload.goal,
        max_concurrent=payload.max_concurrent,
        window_start=payload.window_start or "00:00",
        window_end=payload.window_end or "23:59",
        retry_limit=payload.retry_limit,
        script=payload.script,
        language=payload.language or "hinglish",
        status="draft"
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign

@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str, db: AsyncSession = Depends(get_db)):
    camp_res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = camp_res.scalars().first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    p_res = await db.execute(select(Product).where(Product.id == campaign.product_id))
    product = p_res.scalars().first()

    return {
        "campaign": campaign,
        "product": product
    }

@router.post("/{campaign_id}/start")
async def start_campaign(campaign_id: str):
    await dispatcher.start_campaign(campaign_id)
    return {"status": "success", "message": f"Campaign {campaign_id} started"}

@router.post("/{campaign_id}/pause")
async def pause_campaign(campaign_id: str):
    await dispatcher.pause_campaign(campaign_id)
    return {"status": "success", "message": f"Campaign {campaign_id} paused"}

@router.post("/{campaign_id}/stop")
async def stop_campaign(campaign_id: str):
    await dispatcher.stop_campaign(campaign_id)
    return {"status": "success", "message": f"Campaign {campaign_id} stopped"}

@router.post("/{campaign_id}/contacts/import")
async def import_contacts_csv(
    campaign_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Imports contacts from CSV. Expected headers: name, phone (E.164), language (optional), notes (optional), email (optional).
    Rejects invalid rows with clear messages.
    """
    content = await file.read()
    try:
        decoded = content.decode("utf-8-sig")
    except Exception:
        decoded = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(decoded))
    imported = 0
    rejected = []

    # E.164 phone pattern (e.g. +919876543210 or 10-12 digits)
    phone_pattern = re.compile(r"^\+?[1-9]\d{7,14}$")

    for idx, row in enumerate(reader, start=2): # row 1 is header
        # Normalize keys (strip whitespace, lowercase)
        norm_row = {k.strip().lower(): (v.strip() if v else "") for k, v in row.items() if k}
        name = norm_row.get("name") or norm_row.get("full_name") or norm_row.get("customer_name")
        phone = norm_row.get("phone") or norm_row.get("phone_number") or norm_row.get("mobile")
        email = norm_row.get("email")
        language = norm_row.get("language") or norm_row.get("preferred_language") or "hinglish"
        notes = norm_row.get("notes") or norm_row.get("remark") or norm_row.get("reason_for_calling")

        if not name:
            rejected.append({"row": idx, "reason": "Missing contact name"})
            continue

        if not phone:
            rejected.append({"row": idx, "reason": f"Missing phone number for {name}"})
            continue

        # Clean phone
        clean_phone = re.sub(r"[\s\-\(\)]", "", phone)
        if not clean_phone.startswith("+"):
            if len(clean_phone) == 10:
                clean_phone = "+91" + clean_phone
            else:
                clean_phone = "+" + clean_phone

        if not phone_pattern.match(clean_phone):
            rejected.append({"row": idx, "reason": f"Invalid phone format: '{phone}'. Must be valid E.164."})
            continue

        # Add contact
        contact = Contact(
            campaign_id=campaign_id,
            name=name,
            phone=clean_phone,
            email=email if email else None,
            language=language.lower() if language else "hinglish",
            notes=notes,
            status="new"
        )
        db.add(contact)
        imported += 1

    await db.commit()
    return {
        "status": "success",
        "imported_count": imported,
        "rejected_count": len(rejected),
        "rejected_details": rejected[:20]
    }

@router.get("/{campaign_id}/stats")
async def get_campaign_stats(campaign_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns funnel data and headline counters:
    contacts -> called -> connected -> interested -> order confirmed
    """
    # 1. Contacts
    c_res = await db.execute(select(func.count(Contact.id)).where(Contact.campaign_id == campaign_id))
    total_contacts = c_res.scalar() or 0

    # 2. Called (any call placed)
    calls_res = await db.execute(select(func.count(Call.id)).where(Call.campaign_id == campaign_id))
    total_calls = calls_res.scalar() or 0

    # 3. Connected (duration > 0 or status completed)
    conn_res = await db.execute(
        select(func.count(Call.id)).where(
            and_(
                Call.campaign_id == campaign_id,
                Call.duration_sec > 0
            )
        )
    )
    connected_calls = conn_res.scalar() or 0

    # 4. Interested
    int_res = await db.execute(
        select(func.count(Call.id)).where(
            and_(
                Call.campaign_id == campaign_id,
                Call.outcome.in_(["interested", "order_confirmed", "callback_requested"])
            )
        )
    )
    interested_calls = int_res.scalar() or 0

    # 5. Orders confirmed
    orders_res = await db.execute(
        select(func.count(Call.id)).where(
            and_(
                Call.campaign_id == campaign_id,
                Call.outcome == "order_confirmed"
            )
        )
    )
    orders_confirmed = orders_res.scalar() or 0

    # 6. Callbacks pending
    cb_res = await db.execute(
        select(func.count(Call.id)).where(
            and_(
                Call.campaign_id == campaign_id,
                Call.outcome == "callback_requested"
            )
        )
    )
    callbacks_count = cb_res.scalar() or 0

    # 7. Avg duration
    avg_res = await db.execute(
        select(func.avg(Call.duration_sec)).where(
            and_(Call.campaign_id == campaign_id, Call.duration_sec > 0)
        )
    )
    avg_duration = round(avg_res.scalar() or 0, 1)

    return {
        "funnel": {
            "contacts": total_contacts,
            "called": total_calls,
            "connected": connected_calls,
            "interested": interested_calls,
            "order_confirmed": orders_confirmed
        },
        "counters": {
            "total_calls": total_calls,
            "connected_calls": connected_calls,
            "orders_confirmed": orders_confirmed,
            "callbacks_pending": callbacks_count,
            "avg_duration_sec": avg_duration
        }
    }

