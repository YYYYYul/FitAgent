import uuid
from sqlalchemy import Column, String, Integer, Text, ForeignKey, JSON
from app.db.base import Base, TimestampMixin


class TrainingPlan(Base, TimestampMixin):
    __tablename__ = "training_plan"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), default="active")  # active / completed / archived
    goal = Column(String(50))
    weekly_days = Column(Integer)
    plan_data = Column(JSON, nullable=False)
    plan_summary = Column(Text)
    version = Column(Integer, default=1)
