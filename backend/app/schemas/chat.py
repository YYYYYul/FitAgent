from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: Optional[str] = None


class ConfirmationRequest(BaseModel):
    session_id: str
    confirmed: bool  # True=confirm, False=cancel


class ChatEvent(BaseModel):
    type: str  # "thinking" | "intent" | "plan" | "tool_call" | "tool_result" | "text" | "done" | "error" | "confirmation_required" | "replan" | "rag"
    content: str
    data: Optional[dict] = None
