import uuid
from sqlalchemy import Column, String, Integer, Date, Text, ForeignKey, JSON, Index
from app.db.base import Base, TimestampMixin


class WorkoutLog(Base, TimestampMixin):
    __tablename__ = "workout_log"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(String(36), ForeignKey("training_plan.id", ondelete="SET NULL"), nullable=True)
    date = Column(Date, nullable=False)
    raw_text = Column(Text, nullable=False)
    parsed_record = Column(JSON)
    duration_min = Column(Integer)
    rpe = Column(Integer)

    __table_args__ = (
        Index("idx_workout_user_date", "user_id", "date"),
    )
