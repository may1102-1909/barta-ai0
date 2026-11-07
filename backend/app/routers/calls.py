from typing import Optional, List
from datetime import datetime
import pytz
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Call, Contact, Campaign

router = APIRouter(prefix="/calls", tags=["Calls"])
IST = pytz.timezone("Asia/Kolkata")

@router.get("")
async def list_calls(
    campaign_id: Optional[str] = Query(None),
    outcome: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Call).order_by(desc(Call.started_at)).limit(limit).offset(offset)
    conditions = []
    if campaign_id:
        conditions.append(Call.campaign_id == campaign_id)
    if outcome:
        conditions.append(Call.outcome == outcome)
    
    if conditions:
        stmt = stmt.where(and_(*conditions))

    result = await db.execute(stmt)
    calls = result.scalars().all()

    output = []
    for c in calls:
        # Load contact info
        c_res = await db.execute(select(Contact).where(Contact.id == c.contact_id))
        contact = c_res.scalars().first()

        camp_res = await db.execute(select(Campaign).where(Campaign.id == c.campaign_id))
        campaign = camp_res.scalars().first()

        # Format IST started_at
        started_at_ist = None
        if c.started_at:
            started_at_ist = c.started_at.replace(tzinfo=pytz.utc).astimezone(IST).strftime("%d %b %Y, %I:%M %p IST")

        output.append({
            "id": c.id,
            "contact_name": contact.name if contact else "Unknown",
            "contact_phone": contact.phone if contact else "Unknown",
            "campaign_name": campaign.name if campaign else "Campaign",
            "status": c.status,
            "outcome": c.outcome or "in_progress",
            "duration_sec": c.duration_sec,
            "started_at": started_at_ist,
            "summary": c.summary or "Summary in progress...",
            "transcript_turns": len(c.transcript or [])
        })

    return output

@router.get("/{call_id}")
async def get_call_detail(call_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Call).where(Call.id == call_id))
    call = result.scalars().first()
    if not call:
        raise HTTPException(status_code=404, detail="Call record not found")

    contact_res = await db.execute(select(Contact).where(Contact.id == call.contact_id))
    contact = contact_res.scalars().first()

    started_at_ist = None
    if call.started_at:
        started_at_ist = call.started_at.replace(tzinfo=pytz.utc).astimezone(IST).strftime("%d %b %Y, %I:%M:%S %p IST")

    return {
        "id": call.id,
        "contact_id": call.contact_id,
        "contact_name": contact.name if contact else "Unknown",
        "contact_phone": contact.phone if contact else "Unknown",
        "contact_email": contact.email if contact else None,
        "language_preferred": contact.language if contact else "hinglish",
        "status": call.status,
        "outcome": call.outcome,
        "duration_sec": call.duration_sec,
        "started_at_ist": started_at_ist,
        "summary": call.summary,
        "transcript": call.transcript or [],
        "twilio_sid": call.twilio_sid
    }

