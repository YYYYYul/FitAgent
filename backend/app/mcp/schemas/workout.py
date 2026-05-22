"""MCP schemas for log_workout_record tool."""

from pydantic import BaseModel, Field
from typing import Optional


class MCPLogWorkoutRequest(BaseModel):
    raw_text: str = Field(..., min_length=1, description="Natural language workout description")
    user_id: Optional[str] = None
    date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Workout date YYYY-MM-DD")
