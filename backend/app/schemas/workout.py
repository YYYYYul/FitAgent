from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class LogWorkoutRequest(BaseModel):
    raw_text: str
    date: Optional[str] = None  # "YYYY-MM-DD", defaults to today


class ParsedExercise(BaseModel):
    name: str
    sets: Optional[int] = None
    reps: Optional[int] = None
    weight_kg: Optional[float] = None
    rpe: Optional[int] = None


class ParsedRecord(BaseModel):
    date: str
    focus: Optional[str] = None
    duration_min: Optional[int] = None
    exercises: list[ParsedExercise] = []
    rpe: Optional[int] = Field(default=None, ge=1, le=10)
    notes: Optional[str] = None


class PlanConsistency(BaseModel):
    matched_plan_day: Optional[str] = None
    completion_rate: Optional[float] = None


class LogWorkoutResponse(BaseModel):
    success: bool
    log_id: Optional[str] = None
    parsed_record: Optional[ParsedRecord] = None
    plan_consistency: Optional[PlanConsistency] = None
    error: Optional[str] = None


class WorkoutLogItem(BaseModel):
    id: str
    date: str
    raw_text: str
    parsed_record: Optional[dict]
    duration_min: Optional[int]
    rpe: Optional[int]

    model_config = {"from_attributes": True}


class MonthlySummary(BaseModel):
    year: int
    month: int
    planned_days: int
    completed_days: int
    completion_rate: float
    streak_days: int
    total_duration_min: int
    by_focus: dict[str, int]
    daily_logs: list[dict]
