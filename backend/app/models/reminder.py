import uuid
from sqlalchemy import Column, String, Integer, ForeignKey
from app.db.base import Base, TimestampMixin


class ReminderJob(Base, TimestampMixin):
    __tablename__ = "reminder_job"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(String(36), ForeignKey("training_plan.id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Mon ... 6=Sun
    remind_time = Column(String(5), nullable=False)  # "HH:MM"
    channel = Column(String(50), default="web")
    status = Column(String(20), default="active")  # active / paused / deleted
