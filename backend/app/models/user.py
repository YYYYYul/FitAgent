import uuid
from sqlalchemy import Column, String, Float, Integer
from app.db.base import Base, TimestampMixin


class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profile"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100))

    # Fitness profile
    height_cm = Column(Float)
    weight_kg = Column(Float)
    goal = Column(String(50))  # fat_loss / muscle_gain / health
    training_location = Column(String(50))  # home / gym
    weekly_days = Column(Integer)
    experience_level = Column(String(50))  # beginner / intermediate / advanced
    preferred_time = Column(String(5))  # "HH:MM"
