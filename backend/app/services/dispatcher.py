import asyncio
import logging
from datetime import datetime, timezone
import pytz
from typing import Dict, Set
from sqlalchemy import select, update, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Campaign, Contact, Call, Product
from app.database import AsyncSessionLocal
from app.services.twilio_service import TwilioService

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")

class CampaignDispatcher:
    """
    Manages campaign state, active call concurrency slots (1 or 3-5),
    calling window enforcement in IST, atomic contact claiming, and retry rules.
    """

    def __init__(self):
        self.twilio_service = TwilioService()
        self._active_campaign_tasks: Dict[str, asyncio.Task] = {}
        self._active_call_slots: Dict[str, Set[str]] = {} # campaign_id -> set of active call_ids
        self._stopped_campaigns: Set[str] = set()

    def is_in_calling_window(self, window_start: str, window_end: str) -> bool:
        """Checks if current time in IST falls within campaign calling window."""
        try:
            now_ist = datetime.now(IST).time()
            start_parts = [int(p) for p in window_start.split(":")]
            end_parts = [int(p) for p in window_end.split(":")]
            
            start_time = datetime.now(IST).replace(hour=start_parts[0], minute=start_parts[1], second=0, microsecond=0).time()
            end_time = datetime.now(IST).replace(hour=end_parts[0], minute=end_parts[1], second=0, microsecond=0).time()
            
            return start_time <= now_ist <= end_time
        except Exception as e:
            logger.warning(f"Error checking calling window: {e}. Defaulting to True.")
            return True

    async def start_campaign(self, campaign_id: str):
        """Starts or resumes background dialing for a campaign."""
        self._stopped_campaigns.discard(campaign_id)
        if campaign_id in self._active_campaign_tasks and not self._active_campaign_tasks[campaign_id].done():
            logger.info(f"Campaign {campaign_id} is already running.")
            return

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Campaign).where(Campaign.id == campaign_id))
            campaign = result.scalars().first()
            if not campaign:
                return
            campaign.status = "active"
            await session.commit()

        task = asyncio.create_task(self._campaign_loop(campaign_id))
        self._active_campaign_tasks[campaign_id] = task
        logger.info(f"Campaign {campaign_id} started.")

    async def pause_campaign(self, campaign_id: str):
        """Pauses a campaign. Stops new dials, active calls finish naturally."""
        self._stopped_campaigns.add(campaign_id)
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Campaign).where(Campaign.id == campaign_id))
            campaign = result.scalars().first()
            if campaign:
                campaign.status = "paused"
                await session.commit()
        logger.info(f"Campaign {campaign_id} paused.")

    async def stop_campaign(self, campaign_id: str):
        """Stops a campaign completely."""
        self._stopped_campaigns.add(campaign_id)
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Campaign).where(Campaign.id == campaign_id))
            campaign = result.scalars().first()
            if campaign:
                campaign.status = "completed"
                await session.commit()
        logger.info(f"Campaign {campaign_id} stopped.")

    def on_call_completed(self, campaign_id: str, call_id: str):
        """Notifies the dispatcher that an active call slot has freed up."""
        if campaign_id in self._active_call_slots:
            self._active_call_slots[campaign_id].discard(call_id)
            logger.info(f"Slot freed for campaign {campaign_id}. Active: {len(self._active_call_slots[campaign_id])}")

    async def _campaign_loop(self, campaign_id: str):
        """Main dispatcher loop running while campaign is active."""
        if campaign_id not in self._active_call_slots:
            self._active_call_slots[campaign_id] = set()

        while campaign_id not in self._stopped_campaigns:
            try:
                async with AsyncSessionLocal() as session:
                    camp_res = await session.execute(select(Campaign).where(Campaign.id == campaign_id))
                    campaign = camp_res.scalars().first()
                    if not campaign or campaign.status != "active":
                        break

                    # Check calling window
                    if not self.is_in_calling_window(campaign.window_start, campaign.window_end):
                        logger.info(f"Campaign {campaign_id}: Outside calling window ({campaign.window_start} - {campaign.window_end} IST). Sleeping 30s.")
                        await asyncio.sleep(30)
                        continue

                    # Check concurrency limit
                    active_count = len(self._active_call_slots[campaign_id])
                    max_concurrent = max(1, campaign.max_concurrent or 1)

                    if active_count >= max_concurrent:
                        await asyncio.sleep(1)
                        continue

                    # Atomically claim the next eligible contact
                    # Eligible: status == 'new' and status != 'dnc'
                    contact = await self._claim_next_contact(session, campaign_id)
                    if not contact:
                        # Check if any contacts are still dialing
                        dialing_res = await session.execute(
                            select(func.count(Contact.id)).where(
                                and_(Contact.campaign_id == campaign_id, Contact.status == "dialing")
                            )
                        )
                        dialing_count = dialing_res.scalar() or 0
                        if dialing_count == 0 and active_count == 0:
                            logger.info(f"Campaign {campaign_id} has exhausted all contacts. Marking completed.")
                            campaign.status = "completed"
                            await session.commit()
                            break
                        
                        await asyncio.sleep(2)
                        continue

                    # Create call record
                    call = Call(
                        contact_id=contact.id,
                        campaign_id=campaign_id,
                        status="queued",
                        started_at=datetime.now(timezone.utc)
                    )
                    session.add(call)
                    await session.commit()
                    await session.refresh(call)

                    # Reserve slot
                    self._active_call_slots[campaign_id].add(call.id)

                    # Trigger Twilio outbound call
                    sid = await self.twilio_service.place_call(
                        to_phone=contact.phone,
                        call_id=call.id,
                        contact_id=contact.id,
                        campaign_id=campaign_id
                    )
                    if sid:
                        call.twilio_sid = sid
                        call.status = "in-progress"
                        await session.commit()
                    else:
                        call.status = "failed"
                        call.outcome = "twilio_dial_failed"
                        call.ended_at = datetime.now(timezone.utc)
                        contact.status = "failed"
                        self._active_call_slots[campaign_id].discard(call.id)
                        await session.commit()

            except Exception as e:
                logger.error(f"Error in campaign loop for {campaign_id}: {e}", exc_info=True)
                await asyncio.sleep(3)

        logger.info(f"Exited loop for campaign {campaign_id}.")

    async def _claim_next_contact(self, session: AsyncSession, campaign_id: str) -> Contact | None:
        """
        Atomically selects and marks a contact as 'dialing' so no two workers dial the same contact.
        """
        stmt = (
            select(Contact)
            .where(and_(
                Contact.campaign_id == campaign_id,
                Contact.status == "new"
            ))
            .limit(1)
            .with_for_update() if session.bind.dialect.name == "postgresql" else select(Contact).where(
                and_(Contact.campaign_id == campaign_id, Contact.status == "new")
            ).limit(1)
        )
        result = await session.execute(stmt)
        contact = result.scalars().first()

        if contact:
            contact.status = "dialing"
            contact.attempts += 1
            contact.last_attempt_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(contact)
            return contact

        return None

dispatcher = CampaignDispatcher()

