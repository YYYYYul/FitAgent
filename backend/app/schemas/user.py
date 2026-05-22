from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import time


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)
    display_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    height_cm: Optional[float] = Field(default=None, gt=0, le=300)
    weight_kg: Optional[float] = Field(default=None, gt=0, le=500)
    goal: Optional[str] = None  # fat_loss / muscle_gain / health
    training_location: Optional[str] = None  # home / gym
    weekly_days: Optional[int] = Field(default=None, ge=1, le=7)
    experience_level: Optional[str] = None  # beginner / intermediate / advanced
    preferred_time: Optional[str] = None  # "HH:MM"


class UserProfileResponse(BaseModel):
    id: str
    email: str
    display_name: Optional[str]
    height_cm: Optional[float]
    weight_kg: Optional[float]
    goal: Optional[str]
    training_location: Optional[str]
    weekly_days: Optional[int]
    experience_level: Optional[str]
    preferred_time: Optional[str]

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse
