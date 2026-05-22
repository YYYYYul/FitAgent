"""
Agent Trace Logger - records every agent execution for observability.
This is a core differentiator for interview demos.
"""

import uuid
import time
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.trace import AgentTrace


class TraceLogger:
    """Context manager for agent trace logging."""

    def __init__(self, db: AsyncSession, user_id: str, session_id: str):
        self.db = db
        self.user_id = user_id
        self.session_id = session_id
        self.trace = AgentTrace(
            id=str(uuid.uuid4()),
            user_id=user_id,
            session_id=session_id,
        )
        self.start_time = None

    async def __aenter__(self):
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            self.trace.latency_total_ms = int((time.time() - self.start_time) * 1000)
        self.db.add(self.trace)
        await self.db.flush()

    def log_intent(self, intent: str, confidence: float):
        self.trace.intent = intent
        self.trace.intent_confidence = confidence

    def log_plan_steps(self, steps: list[str]):
        self.trace.plan_steps = steps

    def log_tool_call(self, tool_name: str, params: dict, result: dict, latency_ms: int = 0):
        if self.trace.tools_called is None:
            self.trace.tools_called = []
        self.trace.tools_called.append({
            "tool_name": tool_name,
            "params": params,
            "result": result,
            "latency_ms": latency_ms,
        })

    def log_rag(self, queries: list[str], sources: list[dict]):
        self.trace.rag_queries = {"queries": queries, "sources": sources}

    def log_replan(self, reason: str):
        self.trace.replan_reason = reason

    def log_confirmation(self, target: str, result: str, waited_ms: int = 0):
        """Log HITL confirmation gate activity (Phase 2C Step 2)."""
        if self.trace.tools_called is None:
            self.trace.tools_called = []
        self.trace.tools_called.append({
            "tool": "confirmation_gate",
            "confirmation_target": target,
            "confirmation_result": result,  # "required" | "confirmed" | "cancelled" | "timeout"
            "confirmation_waited_ms": waited_ms,
        })

    def log_response(self, response: str):
        self.trace.final_response = response

    def log_error(self, error: str):
        self.trace.final_response = f"ERROR: {error}"
        self.trace.replan_reason = error

    def get_summary(self) -> dict:
        """Return a human-readable trace summary for debugging/display."""
        return {
            "trace_id": str(self.trace.id),
            "user_id": self.trace.user_id,
            "session_id": str(self.trace.session_id),
            "intent": self.trace.intent,
            "intent_confidence": self.trace.intent_confidence,
            "tools_called": [
                t.get("tool_name") or t.get("tool", "unknown")
                for t in (self.trace.tools_called or [])
            ],
            "latency_ms": self.trace.latency_total_ms,
            "replan_reason": self.trace.replan_reason,
        }


async def get_recent_traces(db: AsyncSession, user_id: str, limit: int = 10) -> list[dict]:
    """Retrieve recent traces for a user (for debugging UI)."""
    from sqlalchemy import select
    result = await db.execute(
        select(AgentTrace)
        .where(AgentTrace.user_id == user_id)
        .order_by(AgentTrace.created_at.desc())
        .limit(limit)
    )
    traces = result.scalars().all()
    return [
        {
            "id": str(t.id),
            "session_id": str(t.session_id),
            "intent": t.intent,
            "intent_confidence": t.intent_confidence,
            "tools_called": t.tools_called,
            "final_response": t.final_response[:200] if t.final_response else None,
            "latency_ms": t.latency_total_ms,
            "created_at": str(t.created_at),
        }
        for t in traces
    ]
