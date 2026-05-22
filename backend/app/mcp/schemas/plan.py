"""
MCP Schemas — Pydantic models for MCP tool arguments (Phase 3B Step 1).

These mirror the existing Pydantic schemas in app/schemas/plan.py but are
kept separate to avoid coupling the MCP layer to the API layer.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal


class MCPGeneratePlanRequest(BaseModel):
    """MCP tool arguments for generate_training_plan."""

    user_id: Optional[str] = Field(None, description="User ID. If omitted, uses MCP_DEMO_USER_ID")
    goal: Literal["fat_loss", "muscle_gain", "health"]
    height_cm: float = Field(gt=0, le=300)
    weight_kg: float = Field(gt=0, le=500)
    training_location: Literal["home", "gym"]
    weekly_days: int = Field(ge=1, le=7)
    experience_level: Literal["beginner", "intermediate", "advanced"]
    preferred_time: str = Field(default="19:00", pattern=r"^\d{2}:\d{2}$")
