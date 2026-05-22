"""
Chat API — SSE streaming endpoint for FitAgent.

Orchestration flow:
  1. Load user context (profile + active plan) from DB
  2. Guardrails → validate input
  3. Intent Router → classify_intent (LLM + keyword fallback)
  4. Route to intent handler node
  5. [HITL] Confirmation gate (Phase 2C Step 2) — pause for user confirmation
  6. Log Agent Trace
  7. Stream response back via SSE

LLM Client is created once as a module-level singleton and injected into all nodes.
"""

import uuid
import json
import time as time_module
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.chat import ChatRequest, ConfirmationRequest
from app.core.agent.state import AgentState
from app.core.agent.llm_client import LLMClient
from app.core.agent.intent import classify_intent
from app.core.agent.guardrails import validate_input, sanitize_response
from app.core.agent.nodes.casual_chat import casual_chat_node
from app.core.agent.nodes.fitness_qa import fitness_qa_node
from app.core.agent.nodes.log_workout import log_workout_node
from app.core.agent.nodes.query_history import query_history_node
from app.core.agent.nodes.create_plan import create_plan_node  # kept as fallback
from app.core.agent.nodes.per_subgraph import per_orchestrator_node  # Phase 2B: PER flow
from app.core.agent.confirmation_store import save_pending, get_pending, delete_pending, is_expired
from app.core.trace.logger import TraceLogger
from app.services.user_service import get_user_by_id
from app.services.plan_service import get_active_plan

router = APIRouter(prefix="/chat", tags=["Chat"])

# Singleton LLM Client — created once at module load, reused across all requests
_llm_client = LLMClient()


async def _event_stream(
    user_id: str,
    message: str,
    session_id: str,
    db: AsyncSession,
    llm_client=None,
):
    """Generator yielding SSE events as the agent processes the request."""
    try:
        # Load user context
        user = await get_user_by_id(db, user_id)
        user_profile = None
        if user:
            user_profile = {
                "id": str(user.id),
                "email": user.email,
                "display_name": user.display_name,
                "height_cm": user.height_cm,
                "weight_kg": user.weight_kg,
                "goal": user.goal,
                "training_location": user.training_location,
                "weekly_days": user.weekly_days,
                "experience_level": user.experience_level,
                "preferred_time": str(user.preferred_time) if user.preferred_time else None,
            }

        active_plan = await get_active_plan(db, user_id)
        active_plan_data = None
        if active_plan:
            active_plan_data = {
                "id": str(active_plan.id),
                "goal": active_plan.goal,
                "weekly_days": active_plan.weekly_days,
                "plan_data": active_plan.plan_data,
                "plan_summary": active_plan.plan_summary,
            }

        # Start trace
        trace = TraceLogger(db, user_id, session_id)
        async with trace:

            # Step 1: Guardrails
            is_valid, error_msg = validate_input(message)
            if not is_valid:
                yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
                trace.log_error(error_msg)
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

            # Step 2: Intent Router
            yield f"data: {json.dumps({'type': 'thinking', 'content': '正在分析你的意图...'})}\n\n"

            intent_result = await classify_intent(message, llm_client)
            intent = intent_result["intent"]
            confidence = intent_result["confidence"]
            trace.log_intent(intent, confidence)

            yield f"data: {json.dumps({'type': 'intent', 'content': intent, 'data': {'confidence': confidence, 'reason': intent_result.get('reason', '')}})}\n\n"

            # Build state
            state: AgentState = {
                "user_input": message,
                "user_id": user_id,
                "session_id": session_id,
                "messages": [],
                "user_profile": user_profile,
                "active_plan": active_plan_data,
                "conversation_history": [],
                "intent": intent,
                "intent_confidence": confidence,
                "plan_steps": [],
                "current_step": 0,
                "replan_count": 0,
                "replan_reason": None,
                "tool_results": [],
                "rag_context": None,
                "rag_sources": [],
                "final_response": "",
                "requires_confirmation": False,
                "confirmation_target": None,
                "error": None,
                "trace_start_ms": time_module.time() * 1000,
                "tools_called": [],
            }

            # Step 3: Route to intent handler
            yield f"data: {json.dumps({'type': 'thinking', 'content': '正在处理你的请求...'})}\n\n"

            if intent == "casual_chat":
                result = await casual_chat_node(state, llm_client)
            elif intent == "fitness_qa":
                result = await fitness_qa_node(state, llm_client)
            elif intent in ("create_plan", "update_plan"):
                # Phase 2B: Plan → Execute → Observe flow
                result = await per_orchestrator_node(state, db, llm_client)

                # Phase 2C Step 2: HITL confirmation gate
                if result.get("requires_confirmation"):
                    # Save pending state for later recovery
                    pending_state = result.pop("_pending_state", None)
                    if pending_state:
                        save_pending(
                            session_id=session_id,
                            user_id=user_id,
                            state=pending_state,
                            confirmation_target=result.get("confirmation_target", ""),
                            confirmation_context=result.get("confirmation_context", {}),
                        )
                        confirmation_context = result.get("confirmation_context", {})
                        yield f"data: {json.dumps({'type': 'confirmation_required', 'content': '需要你的确认', 'data': {'target': result.get('confirmation_target'), 'title': confirmation_context.get('title', ''), 'description': confirmation_context.get('description', ''), 'impact': confirmation_context.get('impact', ''), 'session_id': session_id, 'expires_in_seconds': 300}})}\n\n"

                    # Log confirmation required
                    trace.log_confirmation(
                        target=result.get("confirmation_target", ""),
                        result="required",
                    )
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    return  # Stop here — wait for /chat/confirm
            elif intent == "log_workout":
                result = await log_workout_node(state, db, llm_client)
            elif intent == "query_history":
                result = await query_history_node(state, db, llm_client)
            else:
                result = {"final_response": "抱歉，我不太理解你的意思。你可以问我健身知识、让我制定训练计划、或记录今天的训练。", "intent": intent}

            # Step 4: Tool calls made (yield tool events)
            for tool_entry in result.get("tools_called", []):
                trace.log_tool_call(
                    tool_name=tool_entry.get("tool", "unknown"),
                    params=tool_entry.get("params", {}),
                    result=tool_entry.get("result", {}),
                )
                yield f"data: {json.dumps({'type': 'tool_call', 'content': tool_entry.get('tool', ''), 'data': tool_entry.get('result', {})})}\n\n"

            # Step 4b: Log RAG activity (if fitness_qa was used)
            rag_sources = result.get("rag_sources", [])
            if rag_sources:
                trace.log_rag(
                    queries=[state.get("user_input", "")],
                    sources=rag_sources,
                )
                yield f"data: {json.dumps({'type': 'rag', 'content': 'RAG sources retrieved', 'data': {'count': len(rag_sources), 'sources': rag_sources}})}\n\n"

            # Step 4c: Log Replan activity (Phase 2B Step 2 — if PER flow triggered replan)
            replan_action = result.get("replan_action")
            if replan_action and replan_action != "success":
                trace.log_replan(
                    f"action={replan_action} reason={result.get('replan_reason', 'unknown')} count={result.get('replan_count', 0)}"
                )
                yield f"data: {json.dumps({'type': 'replan', 'content': f'Replan: {replan_action}', 'data': {'action': replan_action, 'reason': result.get('replan_reason', ''), 'count': result.get('replan_count', 0)}})}\n\n"

            # Step 5: Final response
            final_response = sanitize_response(result.get("final_response", ""))
            trace.log_response(final_response)

            # Stream response character by character (simulate streaming)
            yield f"data: {json.dumps({'type': 'text', 'content': final_response})}\n\n"

            # Step 6: Trace summary
            trace_summary = trace.get_summary()
            yield f"data: {json.dumps({'type': 'trace', 'content': 'Agent Trace', 'data': trace_summary})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'content': f'处理请求时出错：{str(e)}'})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"


async def _simple_response(
    user_id: str,
    message: str,
    session_id: str,
    db: AsyncSession,
    llm_client=None,
) -> dict:
    """Non-streaming fallback for when SSE is not suitable."""
    user = await get_user_by_id(db, user_id)
    user_profile = None
    if user:
        user_profile = {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "height_cm": user.height_cm,
            "weight_kg": user.weight_kg,
            "goal": user.goal,
            "training_location": user.training_location,
            "weekly_days": user.weekly_days,
            "experience_level": user.experience_level,
            "preferred_time": str(user.preferred_time) if user.preferred_time else None,
        }

    active_plan = await get_active_plan(db, user_id)
    active_plan_data = None
    if active_plan:
        active_plan_data = {
            "id": str(active_plan.id),
            "goal": active_plan.goal,
            "weekly_days": active_plan.weekly_days,
            "plan_data": active_plan.plan_data,
            "plan_summary": active_plan.plan_summary,
        }

    async with TraceLogger(db, user_id, session_id) as trace:
        is_valid, error_msg = validate_input(message)
        if not is_valid:
            trace.log_error(error_msg)
            return {"response": error_msg, "intent": "blocked", "trace": trace.get_summary()}

        intent_result = await classify_intent(message, llm_client)
        intent = intent_result["intent"]
        trace.log_intent(intent, intent_result["confidence"])

        state: AgentState = {
            "user_input": message,
            "user_id": user_id,
            "session_id": session_id,
            "messages": [],
            "user_profile": user_profile,
            "active_plan": active_plan_data,
            "conversation_history": [],
            "intent": intent,
            "intent_confidence": intent_result["confidence"],
            "plan_steps": [],
            "current_step": 0,
            "replan_count": 0,
            "replan_reason": None,
            "tool_results": [],
            "rag_context": None,
            "rag_sources": [],
            "final_response": "",
            "requires_confirmation": False,
            "confirmation_target": None,
            "error": None,
            "trace_start_ms": time_module.time() * 1000,
            "tools_called": [],
        }

        intent_handlers = {
            "casual_chat": (casual_chat_node, [state, llm_client]),
            "fitness_qa": (fitness_qa_node, [state, llm_client]),
            "create_plan": (per_orchestrator_node, [state, db, llm_client]),  # Phase 2B: PER flow
            "update_plan": (per_orchestrator_node, [state, db, llm_client]),  # Phase 2B: PER flow
            "log_workout": (log_workout_node, [state, db, llm_client]),
            "query_history": (query_history_node, [state, db, llm_client]),
        }

        handler_info = intent_handlers.get(intent)
        if handler_info:
            handler_fn, handler_args = handler_info
            result = await handler_fn(*handler_args)
        else:
            result = {"final_response": "抱歉，我不太理解你的意思。", "intent": intent}

        for tool_entry in result.get("tools_called", []):
            trace.log_tool_call(
                tool_name=tool_entry.get("tool", "unknown"),
                params=tool_entry.get("params", {}),
                result=tool_entry.get("result", {}),
            )

        rag_sources = result.get("rag_sources", [])
        if rag_sources:
            trace.log_rag(
                queries=[message],
                sources=rag_sources,
            )

        replan_action = result.get("replan_action")
        if replan_action and replan_action != "success":
            trace.log_replan(
                f"action={replan_action} reason={result.get('replan_reason', 'unknown')} count={result.get('replan_count', 0)}"
            )

        final_response = sanitize_response(result.get("final_response", ""))
        trace.log_response(final_response)

        return {
            "response": final_response,
            "intent": intent,
            "intent_confidence": intent_result["confidence"],
            "trace": trace.get_summary(),
        }


@router.post("/stream")
async def chat_stream(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """SSE streaming chat endpoint."""
    session_id = req.session_id or str(uuid.uuid4())

    return StreamingResponse(
        _event_stream(
            user_id=req.user_id,
            message=req.message,
            session_id=session_id,
            db=db,
            llm_client=_llm_client,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("")
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Non-streaming chat endpoint (fallback)."""
    session_id = req.session_id or str(uuid.uuid4())

    if not req.user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    result = await _simple_response(
        user_id=req.user_id,
        message=req.message,
        session_id=session_id,
        db=db,
        llm_client=_llm_client,
    )
    return result


# =========================================================================
# Human-in-the-loop: Confirmation endpoint (Phase 2C Step 2a)
# =========================================================================


@router.post("/confirm", response_model=None)
async def confirm_action(
    req: ConfirmationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle user's response to a confirmation_required action.

    - confirmed=true:  resume saved state, continue execution from Execute phase
    - confirmed=false: delete pending state, return cancellation message

    Returns SSE stream on confirm, JSON dict on cancel/error.
    """
    session_id = req.session_id

    # Check 1: pending confirmation exists
    pending = get_pending(session_id)
    if pending is None:
        if is_expired(session_id):
            raise HTTPException(status_code=410, detail="确认已超时，操作自动取消。请重新发起请求。")
        raise HTTPException(status_code=404, detail="没有待确认的操作。可能已经超时或已被处理。")

    # Check 2: confirmed=false → cancel
    if not req.confirmed:
        delete_pending(session_id)
        return {
            "status": "cancelled",
            "message": "操作已取消。你的当前训练计划保持不变。",
            "confirmation_target": pending["confirmation_target"],
        }

    # confirmed=true → resume execution
    saved_state = pending["state"]
    user_id = pending["user_id"]
    saved_state["confirmed"] = True

    # Calculate wait time for trace
    waited_ms = int((time_module.time() - pending["created_at"]) * 1000)

    # Remove from store
    delete_pending(session_id)

    # Resume: stream the rest of execution (Execute → Observe → Replan)
    async def resume_stream():
        try:
            # Re-run PER orchestrator with confirmed=True (it will skip Plan, go to Execute)
            async with TraceLogger(db, user_id, session_id) as trace:
                trace.log_intent("create_plan", 1.0)
                trace.log_confirmation(
                    target=pending["confirmation_target"],
                    result="confirmed",
                    waited_ms=waited_ms,
                )

                result = await per_orchestrator_node(saved_state, db, _llm_client)

                # Emit tool calls
                for tool_entry in result.get("tools_called", []):
                    trace.log_tool_call(
                        tool_name=tool_entry.get("tool", "unknown"),
                        params={},
                        result=tool_entry.get("result", {}),
                    )
                    yield f"data: {json.dumps({'type': 'tool_call', 'content': tool_entry.get('tool', ''), 'data': tool_entry.get('result', {})})}\n\n"

                # Replan events
                replan_action = result.get("replan_action")
                if replan_action and replan_action != "success":
                    trace.log_replan(
                        f"action={replan_action} reason={result.get('replan_reason', 'unknown')} count={result.get('replan_count', 0)}"
                    )
                    yield f"data: {json.dumps({'type': 'replan', 'content': f'Replan: {replan_action}', 'data': {'action': replan_action, 'reason': result.get('replan_reason', ''), 'count': result.get('replan_count', 0)}})}\n\n"

                # Final response
                final_response = sanitize_response(result.get("final_response", ""))
                trace.log_response(final_response)
                yield f"data: {json.dumps({'type': 'text', 'content': final_response})}\n\n"

                # Trace: tools called summary
                tool_names = [
                    t.get("tool_name", t.get("tool", "unknown"))
                    for t in (trace.trace.tools_called or [])
                ]
                yield f"data: {json.dumps({'type': 'trace', 'content': 'Agent Trace', 'data': {'trace_id': str(trace.trace.id), 'intent': 'create_plan', 'tools_called': tool_names}})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': f'处理请求时出错：{str(e)}'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        resume_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
