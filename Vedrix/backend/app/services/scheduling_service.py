import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.scheduling import InterviewSlot, SlotBooking
from app.models.interview import InterviewSession, JobDrive
from app.models.user import User
from app.services.email_service import send_booking_confirmation_email, send_interview_reminder_email

logger = logging.getLogger(__name__)

def generate_ics(booking_id: int, start_time: datetime, end_time: datetime, job_role: str, candidate_name: str, candidate_email: str) -> bytes:
    """
    Generates a raw RFC 5545 compliant iCalendar (.ics) event string as bytes.
    """
    def format_dt(dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    dtstamp = format_dt(datetime.now(timezone.utc))
    dtstart = format_dt(start_time)
    dtend = format_dt(end_time)

    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Vedrix//AI Interview Platform//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:REQUEST",
        "BEGIN:VEVENT",
        f"UID:booking_{booking_id}@vedrix.ai",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART:{dtstart}",
        f"DTEND:{dtend}",
        f"SUMMARY:Vedrix AI Interview - {job_role}",
        f"DESCRIPTION:Your automated AI-powered interview with Vedrix for the {job_role} role. Log into the candidate portal to start when ready.",
        "ORGANIZER;CN=\"Vedrix AI\":MAILTO:no-reply@vedrix.ai",
        f"ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=TRUE;CN=\"{candidate_name}\":MAILTO:{candidate_email}",
        "END:VEVENT",
        "END:VCALENDAR"
    ]
    return "\r\n".join(ics_lines).encode("utf-8")


class SchedulingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_slots(self, drive_id: int, slots_list: List[Dict[str, Any]]) -> List[InterviewSlot]:
        """
        Allows HR/Admin to create multiple slots for a drive.
        """
        # Verify drive exists
        drive_res = await self.db.execute(select(JobDrive).where(JobDrive.id == drive_id))
        if not drive_res.scalars().first():
            raise HTTPException(status_code=404, detail="Job drive not found")

        created_slots = []
        for slot_data in slots_list:
            start_time = slot_data["start_time"]
            end_time = slot_data["end_time"]
            max_candidates = slot_data.get("max_candidates", 1)

            # Standardize timezones
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)

            new_slot = InterviewSlot(
                drive_id=drive_id,
                start_time=start_time,
                end_time=end_time,
                max_candidates=max_candidates,
                booked_count=0
            )
            self.db.add(new_slot)
            created_slots.append(new_slot)

        await self.db.commit()
        for s in created_slots:
            await self.db.refresh(s)
        return created_slots

    async def get_drive_slots(self, drive_id: int) -> List[InterviewSlot]:
        """
        Fetches all slots created for a given recruitment drive.
        """
        result = await self.db.execute(
            select(InterviewSlot)
            .where(InterviewSlot.drive_id == drive_id)
            .order_by(InterviewSlot.start_time.asc())
        )
        return list(result.scalars().all())

    async def book_slot(self, candidate_id: int, slot_id: int) -> SlotBooking:
        """
        Allows a candidate to book a specific interview slot.
        Enforces capacity checks and double-booking prevention.
        Creates a scheduled InterviewSession, triggers confirmation email with .ics attachment.
        """
        # 1. Fetch slot
        slot_res = await self.db.execute(select(InterviewSlot).where(InterviewSlot.id == slot_id))
        slot = slot_res.scalars().first()
        if not slot:
            raise HTTPException(status_code=404, detail="Interview slot not found")

        # 2. Prevent double booking on the same drive
        double_booking_stmt = (
            select(SlotBooking)
            .join(InterviewSlot, SlotBooking.slot_id == InterviewSlot.id)
            .where(
                SlotBooking.candidate_id == candidate_id,
                InterviewSlot.drive_id == slot.drive_id
            )
        )
        double_booking_res = await self.db.execute(double_booking_stmt)
        if double_booking_res.scalars().first():
            raise HTTPException(
                status_code=409,
                detail="You have already booked a slot for this recruitment drive."
            )

        # 3. Capacity check
        if slot.booked_count >= slot.max_candidates:
            raise HTTPException(
                status_code=409,
                detail="This interview slot is already full."
            )

        # 4. Fetch candidate details
        candidate_res = await self.db.execute(select(User).where(User.id == candidate_id))
        candidate = candidate_res.scalars().first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        # 5. Fetch drive details
        drive_res = await self.db.execute(select(JobDrive).where(JobDrive.id == slot.drive_id))
        drive = drive_res.scalars().first()
        if not drive:
            raise HTTPException(status_code=404, detail="Associated recruitment drive not found")

        # 6. Create actual scheduled interview session
        session = InterviewSession(
            candidate_id=candidate_id,
            job_drive_id=slot.drive_id,
            session_type="actual",
            status="scheduled",
            start_time=slot.start_time,
            end_time=slot.end_time
        )
        self.db.add(session)
        await self.db.flush()  # get session.id

        # 7. Create booking record
        booking = SlotBooking(
            slot_id=slot_id,
            candidate_id=candidate_id,
            session_id=session.id,
            reminder_sent=False
        )
        self.db.add(booking)

        # 8. Increment slot count
        slot.booked_count += 1
        self.db.add(slot)

        await self.db.commit()
        await self.db.refresh(booking)

        # 9. Generate ICS & Trigger Confirmation Email
        try:
            ics_bytes = generate_ics(
                booking_id=booking.id,
                start_time=slot.start_time,
                end_time=slot.end_time,
                job_role=drive.job_role,
                candidate_name=f"{candidate.first_name} {candidate.last_name}",
                candidate_email=candidate.email
            )
            await send_booking_confirmation_email(
                to=candidate.email,
                first_name=candidate.first_name,
                job_role=drive.job_role,
                start_time=slot.start_time,
                end_time=slot.end_time,
                ics_content=ics_bytes
            )
        except Exception as e:
            logger.error(f"Failed to send booking confirmation email to {candidate.email}: {e}")

        return booking

    async def send_reminders(self) -> int:
        """
        Scans all bookings scheduled within the next 24 hours and sends a reminder.
        Returns the count of reminders sent.
        """
        now = datetime.now(timezone.utc)
        tomorrow = now + timedelta(hours=24)

        # Query bookings where start_time is between now and tomorrow, and reminder not yet sent
        stmt = (
            select(SlotBooking, InterviewSlot, User, JobDrive)
            .join(InterviewSlot, SlotBooking.slot_id == InterviewSlot.id)
            .join(User, SlotBooking.candidate_id == User.id)
            .join(JobDrive, InterviewSlot.drive_id == JobDrive.id)
            .where(
                and_(
                    InterviewSlot.start_time > now,
                    InterviewSlot.start_time <= tomorrow,
                    SlotBooking.reminder_sent == False
                )
            )
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        sent_count = 0
        for booking, slot, candidate, drive in rows:
            try:
                await send_interview_reminder_email(
                    to=candidate.email,
                    first_name=candidate.first_name,
                    job_role=drive.job_role,
                    start_time=slot.start_time
                )
                booking.reminder_sent = True
                self.db.add(booking)
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send reminder for booking {booking.id} to {candidate.email}: {e}")

        if sent_count > 0:
            await self.db.commit()

        return sent_count
