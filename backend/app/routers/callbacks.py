from typing import Optional
from datetime import datetime, timezone
import pytz
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Callback, Contact, Call

router = APIRouter(prefix="/callbacks", tags=["Callbacks"])
IST = pytz.timezone("Asia/Kolkata")

class RescheduleRequest(BaseModel):
    new_due_at_iso: str

@router.get("")
async def list_callbacks(
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Callback).order_by(Callback.due_at.asc()).limit(limit)
    if status:
        stmt = stmt.where(Callback.status == status)

    result = await db.execute(stmt)
    callbacks = result.scalars().all()

    output = []
    for cb in callbacks:
        contact_res = await db.execute(select(Contact).where(Contact.id == cb.contact_id))
        contact = contact_res.scalars().first()

        due_at_ist = None
        if cb.due_at:
            due_at_ist = cb.due_at.replace(tzinfo=pytz.utc).astimezone(IST).strftime("%d %b %Y, %I:%M %p IST")

        output.append({
            "id": cb.id,
            "contact_name": contact.name if contact else "Unknown",
            "contact_phone": contact.phone if contact else "Unknown",
            "due_at_ist": due_at_ist,
            "due_at_iso": cb.due_at.isoformat() if cb.due_at else None,
            "reason": cb.reason or "Callback requested during call",
            "status": cb.status,
            "created_at": cb.created_at.isoformat() if cb.created_at else None
        })

    return output

@router.post("/{callback_id}/reschedule")
async def reschedule_callback(
    callback_id: str,
    payload: RescheduleRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Callback).where(Callback.id == callback_id))
    cb = result.scalars().first()
    if not cb:
        raise HTTPException(status_code=404, detail="Callback not found")

    try:
        new_due = datetime.fromisoformat(payload.new_due_at_iso.replace("Z", "+00:00"))
        cb.due_at = new_due.astimezone(timezone.utc)
        cb.status = "pending"
        await db.commit()
        return {"status": "success", "message": "Callback rescheduled successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid datetime format: {e}")

@router.post("/{callback_id}/cancel")
async def cancel_callback(callback_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Callback).where(Callback.id == callback_id))
    cb = result.scalars().first()
    if not cb:
        raise HTTPException(status_code=404, detail="Callback not found")

    cb.status = "cancelled"
    await db.commit()
    return {"status": "success", "message": "Callback cancelled"}

