from typing import TypedDict, Optional, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    # ---- User input ----
    user_input: str
    user_id: str
    session_id: str

    # ---- Message history (LangGraph managed) ----
    messages: Annotated[list[BaseMessage], add_messages]

    # ---- Memory / Context (loaded from DB) ----
    user_profile: Optional[dict]
    active_plan: Optional[dict]
    conversation_history: list[dict]

    # ---- Intent ----
    intent: str
    intent_confidence: float

    # ---- Plan-Execute-Observe (Phase 2B) ----
    plan_steps: list[str]           # ordered list of tools to call
    current_step: int               # index of currently executing step
    tool_results: list[dict]        # [{step, tool, success, result}]
    observation_passed: bool        # did all Observe checks pass?
    observation_errors: list[str]   # list of validation failure messages
    replan_count: int               # Phase 2B Step 2: count replan attempts
    replan_reason: Optional[str]    # Phase 2B Step 2: why replan was triggered

    # ---- RAG ----
    rag_context: Optional[str]
    rag_sources: list[dict]

    # ---- Human-in-the-loop (Phase 2C Step 2) ----
    requires_confirmation: bool
    confirmation_target: Optional[str]
    confirmation_context: Optional[dict]     # {title, description, impact, affected_data}
    confirmed: Optional[bool]                # None=waiting, True=confirmed, False=cancelled
    confirmation_expires_at: Optional[float] # Unix timestamp for timeout

    # ---- Output ----
    final_response: str
    error: Optional[str]

    # ---- Trace metadata ----
    trace_start_ms: float
    tools_called: list[dict]
