"""
ReminderEvent — records each time a scheduled reminder fires.

Separate from ReminderJob (which stores the schedule) so we can:
- Track trigger history without touching the job config
- Support queries like "show me recent reminders"
- Keep a clean audit trail for debugging scheduler issues
"""

import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.sqlite import DATETIME
from app.db.base import Base, TimestampMixin


class ReminderEvent(Base):
    __tablename__ = "reminder_event"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False, index=True)
    reminder_job_id = Column(String(36), ForeignKey("reminder_job.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(String(36), ForeignKey("training_plan.id", ondelete="SET NULL"), nullable=True)
    message = Column(Text, nullable=False)           # the reminder text generated
    status = Column(String(20), default="sent")      # sent / failed / skipped
    triggered_at = Column(DateTime, nullable=False)  # when the scheduler fired
    created_at = Column(DateTime, nullable=False)
