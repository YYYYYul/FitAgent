"""MCP schemas for create_weekly_reminder tool."""

from pydantic import BaseModel, Field
from typing import Optional, Literal


class TrainingDayEntry(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday ... 6=Sunday")
    remind_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM format")


class MCPCreateReminderRequest(BaseModel):
    user_id: str = Field(..., description="User ID (UUID)")
    plan_id: str = Field(..., description="Training plan ID (UUID)")
    training_days: list[TrainingDayEntry] = Field(..., min_length=1)
    channel: str = Field(default="web", description="Notification channel")
