import asyncio
import logging
from datetime import datetime, timezone, timedelta
import pytz
from sqlalchemy import select, and_, or_
from app.models import Callback, Contact, Campaign, Call
from app.database import AsyncSessionLocal
from app.services.dispatcher import dispatcher

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")

class CallbackScheduler:
    """
    Background worker that checks every 60 seconds for due callbacks,
    validates the IST calling window, moves out-of-window callbacks to the next morning,
    and enqueues the callback call with previous context.
    """

    def __init__(self):
        self._running = False
        self._task = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Callback Scheduler service started.")

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _poll_loop(self):
        while self._running:
            try:
                await self.process_due_callbacks()
            except Exception as e:
                logger.error(f"Error in callback poll loop: {e}", exc_info=True)
            await asyncio.sleep(60)

    async def process_due_callbacks(self):
        now_utc = datetime.now(timezone.utc)
        now_naive = datetime.utcnow()
        async with AsyncSessionLocal() as session:
            stmt = select(Callback).where(
                and_(
                    Callback.status == "pending",
                    or_(
                        Callback.due_at <= now_utc,
                        Callback.due_at <= now_naive
                    )
                )
            )
            result = await session.execute(stmt)
            due_callbacks = result.scalars().all()

            for cb in due_callbacks:
                # Fetch contact & campaign
                c_stmt = select(Contact).where(Contact.id == cb.contact_id)
                contact = (await session.execute(c_stmt)).scalars().first()
                if not contact:
                    cb.status = "cancelled"
                    continue

                camp_stmt = select(Campaign).where(Campaign.id == contact.campaign_id)
                campaign = (await session.execute(camp_stmt)).scalars().first()
                if not campaign:
                    continue

                # Check calling window in IST
                if not dispatcher.is_in_calling_window(campaign.window_start, campaign.window_end):
                    # Move to next window opening (09:00 IST)
                    logger.info(f"Callback {cb.id} is outside calling window. Moving to next window opening.")
                    now_ist = datetime.now(IST)
                    # Next morning at window_start
                    start_parts = [int(p) for p in campaign.window_start.split(":")]
                    next_opening = now_ist.replace(hour=start_parts[0], minute=start_parts[1], second=0, microsecond=0)
                    if next_opening <= now_ist:
                        next_opening += timedelta(days=1)
                    cb.due_at = next_opening.astimezone(timezone.utc)
                    await session.commit()
                    continue

                # Inside window: mark callback as in_progress and reset contact to new so dispatcher calls
                cb.status = "in_progress"
                contact.status = "new"
                # Store callback reason into contact notes for LLM context
                contact.notes = f"Callback requested: {cb.reason or 'Follow-up requested'}"

                await session.commit()
                logger.info(f"Callback {cb.id} queued for contact {contact.name} ({contact.phone}).")

                # If campaign is paused, resume it if desired
                if campaign.status == "active":
                    await dispatcher.start_campaign(campaign.id)

scheduler = CallbackScheduler()
