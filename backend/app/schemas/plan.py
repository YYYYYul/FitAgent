from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date


class ExerciseItem(BaseModel):
    name: str
    sets: int
    reps: str
    rest_sec: int
    notes: Optional[str] = None


class DailySchedule(BaseModel):
    day: str  # Monday, Tuesday, ...
    focus: str
    warmup: str
    exercises: list[ExerciseItem]
    cardio: Optional[str] = None
    total_duration_min: int


class GeneratePlanRequest(BaseModel):
    goal: Literal["fat_loss", "muscle_gain", "health"]
    height_cm: float
    weight_kg: float
    training_location: Literal["home", "gym"]
    weekly_days: int = Field(ge=1, le=7)
    experience_level: Literal["beginner", "intermediate", "advanced"]
    preferred_time: str  # "HH:MM"


class GeneratePlanResponse(BaseModel):
    success: bool
    plan_id: Optional[str] = None
    weekly_schedule: Optional[list[DailySchedule]] = None
    plan_summary: Optional[str] = None
    warnings: Optional[list[str]] = None
    error: Optional[str] = None


class PlanSummary(BaseModel):
    id: str
    status: str
    goal: Optional[str]
    weekly_days: Optional[int]
    plan_summary: Optional[str]
    plan_data: Optional[dict]
    created_at: str

    model_config = {"from_attributes": True}
