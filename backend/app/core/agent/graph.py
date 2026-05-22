"""
LangGraph Main Graph — orchestrates the full agent workflow.

Graph structure (Phase 2B):
  START → load_context → guardrails → intent_router
    → [casual_chat | fitness_qa | PER | log_workout | query_history | blocked]
    → END

create_plan now routes through per_orchestrator_node (Plan → Execute → Observe).
"""

import uuid
from typing import Literal
from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent.state import AgentState
from app.core.agent.intent import classify_intent
from app.core.agent.guardrails import validate_input, sanitize_response
from app.core.agent.nodes.casual_chat import casual_chat_node
from app.core.agent.nodes.log_workout import log_workout_node
from app.core.agent.nodes.query_history import query_history_node
from app.core.agent.nodes.create_plan import create_plan_node  # kept as fallback
from app.core.agent.nodes.per_subgraph import per_orchestrator_node  # Phase 2B: PER flow
from app.core.agent.nodes.fitness_qa import fitness_qa_node
from app.core.trace.logger import TraceLogger


async def load_context_node(state: AgentState) -> dict:
    """Load user profile and active plan from DB (injected by caller)."""
    return {}


async def guardrails_node(state: AgentState) -> dict:
    """Validate input before processing."""
    user_input = state.get("user_input", "")
    is_valid, error = validate_input(user_input)
    if not is_valid:
        return {"final_response": error, "error": error, "intent": "blocked"}
    return {}


async def intent_router_node(state: AgentState, llm_client=None) -> dict:
    """Classify user intent."""
    if state.get("error"):
        return {}

    user_input = state.get("user_input", "")
    result = await classify_intent(user_input, llm_client)
    return {
        "intent": result["intent"],
        "intent_confidence": result["confidence"],
    }


def route_by_intent(state: AgentState) -> Literal["casual_chat", "fitness_qa", "create_plan", "log_workout", "query_history", "blocked"]:
    """Route to the appropriate node based on intent."""
    intent = state.get("intent", "casual_chat")
    error = state.get("error")

    if error:
        return "blocked"

    valid_intents = ["casual_chat", "fitness_qa", "create_plan", "log_workout", "query_history"]
    if intent in valid_intents:
        return intent

    return "casual_chat"


async def blocked_node(state: AgentState) -> dict:
    """Handle blocked/error inputs."""
    return {
        "final_response": state.get("error", "抱歉，无法处理这个请求。"),
        "intent": "blocked",
        "requires_confirmation": False,
    }


def build_graph() -> StateGraph:
    """Build and return the LangGraph StateGraph."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("load_context", load_context_node)
    workflow.add_node("guardrails", guardrails_node)
    workflow.add_node("intent_router", intent_router_node)
    workflow.add_node("casual_chat", casual_chat_node)
    workflow.add_node("fitness_qa", fitness_qa_node)
    workflow.add_node("create_plan", per_orchestrator_node)  # Phase 2B: PER flow
    workflow.add_node("log_workout", log_workout_node)
    workflow.add_node("query_history", query_history_node)
    workflow.add_node("blocked", blocked_node)

    # Set entry point
    workflow.set_entry_point("load_context")
    workflow.add_edge("load_context", "guardrails")
    workflow.add_edge("guardrails", "intent_router")

    # Conditional routing
    workflow.add_conditional_edges(
        "intent_router",
        route_by_intent,
        {
            "casual_chat": "casual_chat",
            "fitness_qa": "fitness_qa",
            "create_plan": "create_plan",
            "log_workout": "log_workout",
            "query_history": "query_history",
            "blocked": "blocked",
        },
    )

    # All nodes go to END
    workflow.add_edge("casual_chat", END)
    workflow.add_edge("fitness_qa", END)
    workflow.add_edge("create_plan", END)
    workflow.add_edge("log_workout", END)
    workflow.add_edge("query_history", END)
    workflow.add_edge("blocked", END)

    return workflow


# Singleton graph instance
_agent_graph = None


def get_agent_graph() -> StateGraph:
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_graph()
    return _agent_graph
