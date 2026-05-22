"""
Plan-Execute-Observe-Replan subgraph for create_plan (Phase 2B Step 2).

Workflow:
  Plan Node:       validate user profile → generate plan_steps
  Execute Node:    call tools in order
  Observe Node:    validate results → set observation_passed
  Replan Node:     determine action (request_input | retry_once | simple_fix | graceful_fail)

WHY minimal Replan only:
  Full Replan with user interaction (confirmation, re-input wait) requires
  a stateful LangGraph subgraph with interrupt points. This minimal version
  handles the 4 most common failure modes within a single request cycle,
  keeping complexity low while demonstrating the PER pattern.

Node signatures follow the convention:
  In:  state fields needed for this phase
  Out: dict of state updates for the next phase
"""

# Maximum replan attempts before graceful_fail
MAX_REPLANS = 1

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent.state import AgentState
from app.core.agent.llm_client import LLMClient
from app.core.tools.generate_plan import generate_training_plan
from app.core.tools.create_reminder import create_weekly_reminder
from app.services.plan_service import create_plan, get_active_plan

# Required profile fields for generating a training plan.
# All must be present and non-None; otherwise Plan Node requests input.
REQUIRED_FIELDS = [
    "goal",
    "height_cm",
    "weight_kg",
    "training_location",
    "weekly_days",
    "experience_level",
]

FIELD_LABELS = {
    "goal": "训练目标（减脂/增肌/健康维持）",
    "height_cm": "身高（cm）",
    "weight_kg": "体重（kg）",
    "training_location": "训练地点（在家/健身房）",
    "weekly_days": "每周训练天数（1-7天）",
    "experience_level": "训练经验（新手/中级/高级）",
}

FIELD_EXAMPLE = "例如：「我身高175、体重80、想减脂、在健身房、一周练4天、中级水平」"


# =========================================================================
# Plan Node
# =========================================================================


async def plan_node(
    state: AgentState,
    llm: Optional[LLMClient] = None,
) -> dict:
    """
    Plan Node: validate user profile completeness and generate execution steps.

    In:  state.user_input, state.user_profile
    Out: state.plan_steps (or error with observation_passed=False)
    """
    user_input = state.get("user_input", "")
    user_profile = state.get("user_profile")

    # ---- Check 1: user_profile exists ----
    if not user_profile:
        return {
            "plan_steps": [],
            "observation_passed": False,
            "observation_errors": ["user_profile_not_found"],
            "final_response": (
                "要制定训练计划，我需要先了解你的身体信息。请告诉我：\n"
                "1. 身高（cm）\n"
                "2. 体重（kg）\n"
                "3. 训练目标（减脂/增肌/健康维持）\n"
                "4. 在哪训练（在家/健身房）\n"
                "5. 每周能练几天（1-7天）\n"
                "6. 训练经验（新手/中级/高级）\n\n"
                f"{FIELD_EXAMPLE}"
            ),
            "intent": "create_plan",
            "error": "user_profile_incomplete",
        }

    # ---- Check 2: all required fields are non-None ----
    missing_fields = []
    for field in REQUIRED_FIELDS:
        value = user_profile.get(field)
        if value is None or value == "":
            missing_fields.append(field)

    if missing_fields:
        missing_labels = [f"{FIELD_LABELS.get(f, f)}" for f in missing_fields]
        return {
            "plan_steps": [],
            "observation_passed": False,
            "observation_errors": [f"missing_fields: {','.join(missing_fields)}"],
            "final_response": (
                f"你的个人信息还不完整，缺少：{'、'.join(missing_labels)}。\n\n"
                f"请在个人资料中补充这些信息，然后我就能为你生成专属训练计划！\n\n"
                f"{FIELD_EXAMPLE}"
            ),
            "intent": "create_plan",
            "error": "profile_incomplete",
        }

    # ---- Check 3: HITL confirmation gate (Phase 2C Step 2) ----
    # When user already has an active_plan and requests a new one,
    # we must confirm before overwriting.
    active_plan = state.get("active_plan")
    needs_confirmation = active_plan is not None and active_plan.get("plan_data") is not None

    if needs_confirmation:
        current_goal = active_plan.get("goal", "unknown")
        current_days = active_plan.get("weekly_days", "?")
        return {
            "plan_steps": ["generate_training_plan", "create_weekly_reminder"],
            "current_step": 0,
            "observation_passed": True,
            "observation_errors": [],
            "requires_confirmation": True,
            "confirmation_target": "plan_regeneration",
            "confirmation_context": {
                "title": "确定要重新生成训练计划吗？",
                "description": f"这将覆盖你当前的训练计划（{current_goal}，{current_days}天/周）。旧计划将无法恢复。",
                "impact": "high",
                "affected_data": {
                    "current_plan_goal": current_goal,
                    "current_plan_days": current_days,
                    "will_be_replaced": True,
                },
            },
        }

    # ---- Generate plan_steps ----
    # In this minimal PER, the steps are fixed for create_plan.
    # Phase 2B Step 2 can use LLM to dynamically generate steps.
    plan_steps = ["generate_training_plan", "create_weekly_reminder"]

    return {
        "plan_steps": plan_steps,
        "current_step": 0,
        "observation_passed": True,  # Plan phase passed
        "observation_errors": [],
        "requires_confirmation": False,
    }


# =========================================================================
# Execute Node
# =========================================================================


async def execute_node(
    state: AgentState,
    db: AsyncSession,
    llm: Optional[LLMClient] = None,
) -> dict:
    """
    Execute Node: call each tool in plan_steps sequentially.

    In:  state.plan_steps, state.user_profile, state.user_id
    Out: state.tool_results, state.tools_called

    If any tool fails, execution stops and the error is recorded.
    Subsequent tools are NOT called after a failure.
    """
    user_id = state.get("user_id", "")
    user_profile = state.get("user_profile", {})
    plan_steps = state.get("plan_steps", [])

    tool_results: list[dict] = []
    tools_called: list[dict] = []
    plan_id: Optional[str] = None
    execution_error: Optional[str] = None

    # Extract profile values for tool calls
    goal = user_profile.get("goal", "health")
    height = float(user_profile.get("height_cm", 170))
    weight = float(user_profile.get("weight_kg", 70))
    location = user_profile.get("training_location", "home")
    weekly_days = int(user_profile.get("weekly_days", 3))
    experience = user_profile.get("experience_level", "beginner")
    preferred_time = str(user_profile.get("preferred_time", "19:00"))

    # Store plan generation result for use in subsequent steps
    plan_generation_result = None

    # ---- Execute each step ----
    for step_name in plan_steps:
        if step_name == "generate_training_plan":
            try:
                plan_generation_result = generate_training_plan(
                    goal=goal,
                    height_cm=height,
                    weight_kg=weight,
                    training_location=location,
                    weekly_days=weekly_days,
                    experience_level=experience,
                    preferred_time=preferred_time,
                )
                if plan_generation_result.get("success"):
                    plan_id = plan_generation_result.get("plan_id")
                    # Save plan to DB immediately after generation
                    plan = await create_plan(
                        db=db,
                        user_id=user_id,
                        goal=goal,
                        weekly_days=weekly_days,
                        plan_data={"weekly_schedule": plan_generation_result.get("weekly_schedule", [])},
                        plan_summary=plan_generation_result.get("plan_summary", ""),
                    )
                    plan_id = str(plan.id)
                    tool_results.append({
                        "step": step_name,
                        "tool": "generate_training_plan",
                        "success": True,
                        "result": {"plan_id": plan_id, "plan_summary": plan_generation_result.get("plan_summary", "")},
                    })
                    tools_called.append({
                        "tool": "generate_training_plan",
                        "result": {"plan_id": plan_id, "success": True},
                    })
                else:
                    tool_results.append({
                        "step": step_name,
                        "tool": "generate_training_plan",
                        "success": False,
                        "error": plan_generation_result.get("error", "unknown_error"),
                    })
                    execution_error = plan_generation_result.get("error", "计划生成失败")
                    break  # Stop on first failure
            except Exception as e:
                tool_results.append({
                    "step": step_name,
                    "tool": "generate_training_plan",
                    "success": False,
                    "error": str(e),
                })
                execution_error = f"计划生成异常：{e}"
                break

        elif step_name == "create_weekly_reminder":
            try:
                # Build training_days from the plan that was just generated
                if plan_id and plan_generation_result and plan_generation_result.get("weekly_schedule"):
                    training_days = []
                    for day_plan in plan_generation_result["weekly_schedule"]:
                        day_names_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                        day_idx = day_names_en.index(day_plan["day"]) if day_plan["day"] in day_names_en else 0
                        training_days.append({
                            "day_of_week": day_idx,
                            "remind_time": preferred_time,
                        })

                    reminder_result = await create_weekly_reminder(
                        db=db,
                        user_id=user_id,
                        plan_id=plan_id,
                        training_days=training_days,
                    )

                    tool_results.append({
                        "step": step_name,
                        "tool": "create_weekly_reminder",
                        "success": reminder_result.get("success", False),
                        "result": {"job_count": len(reminder_result.get("reminder_jobs", []))},
                    })
                    tools_called.append({
                        "tool": "create_weekly_reminder",
                        "result": reminder_result,
                    })

                    if not reminder_result.get("success"):
                        execution_error = "提醒创建失败"
                        # NOTE: Plan is already saved. Reminder failure does not roll back
                        # the plan — this is intentional. The user has a valid plan,
                        # they can create reminders later.
                else:
                    tool_results.append({
                        "step": step_name,
                        "tool": "create_weekly_reminder",
                        "success": False,
                        "error": "no_plan_to_create_reminders_for",
                    })
            except Exception as e:
                tool_results.append({
                    "step": step_name,
                    "tool": "create_weekly_reminder",
                    "success": False,
                    "error": str(e),
                })
                execution_error = f"提醒创建异常：{e}"

    return {
        "tool_results": tool_results,
        "tools_called": tools_called,
        "current_step": len(tool_results),
        "observation_errors": [execution_error] if execution_error else [],
    }


# =========================================================================
# Observe Node
# =========================================================================


async def observe_node(
    state: AgentState,
    db: AsyncSession,
) -> dict:
    """
    Observe Node: validate all execution results against business rules.

    In:  state.tool_results, state.user_profile
    Out: state.observation_passed, state.observation_errors, state.final_response

    Validation checks:
      1. generate_training_plan succeeded
      2. Training plan was saved to DB
      3. create_weekly_reminder succeeded (or was skipped with acceptable reason)
      4. Reminder job count matches training_days
      5. plan_data is not empty
    """
    tool_results = state.get("tool_results", [])
    user_profile = state.get("user_profile", {})
    observation_errors: list[str] = []

    # ---- Extract tool results ----
    plan_result = None
    reminder_result = None
    for tr in tool_results:
        if tr.get("tool") == "generate_training_plan":
            plan_result = tr
        elif tr.get("tool") == "create_weekly_reminder":
            reminder_result = tr

    # ---- Check 1: plan generation succeeded ----
    if not plan_result:
        observation_errors.append("generate_training_plan: not executed")
    elif not plan_result.get("success"):
        observation_errors.append(f"generate_training_plan: {plan_result.get('error', 'failed')}")

    # ---- Check 2: plan saved to DB ----
    plan_id = plan_result.get("result", {}).get("plan_id") if plan_result else None
    if plan_id:
        try:
            from app.services.plan_service import get_plan_by_id
            saved_plan = await get_plan_by_id(db, plan_id)
            if not saved_plan:
                observation_errors.append("training_plan: not found in database")
            elif not saved_plan.plan_data:
                observation_errors.append("training_plan: plan_data is empty")
        except Exception as e:
            observation_errors.append(f"training_plan: DB verification failed: {e}")
    else:
        if plan_result and plan_result.get("success"):
            observation_errors.append("training_plan: plan_id missing from successful generation")

    # ---- Check 3 & 4: reminder created correctly ----
    if reminder_result:
        if not reminder_result.get("success"):
            # Reminder failure is a warning, not a blocker for the plan
            obs_error = reminder_result.get("error", "reminder creation failed")
            observation_errors.append(f"create_weekly_reminder: {obs_error} (plan saved, reminders can be recreated)")
        else:
            weekly_days = int(user_profile.get("weekly_days", 0))
            job_count = reminder_result.get("result", {}).get("job_count", 0)
            if job_count != weekly_days and weekly_days > 0:
                observation_errors.append(
                    f"reminder_job count mismatch: expected {weekly_days}, got {job_count}"
                )

    # ---- Determine overall result ----
    # Critical errors (plan generation/save failure) → observation_passed = False
    # Non-critical errors (reminder failure) → observation_passed = True but logged
    critical_errors = [e for e in observation_errors if "generate_training_plan" in e or "not found" in e or "plan_data is empty" in e or "plan_id missing" in e]

    if critical_errors:
        return {
            "observation_passed": False,
            "observation_errors": observation_errors,
            "final_response": (
                f"训练计划生成过程中出现问题：\n"
                + "\n".join(f"  • {e}" for e in observation_errors)
                + "\n\n请稍后重试，或检查你的个人信息是否完整。"
            ),
        }

    # ---- Success response ----
    passed = len([e for e in observation_errors if "reminder" not in e]) == 0

    # Build success response from plan data
    if plan_result and plan_result.get("success"):
        summary = plan_result.get("result", {}).get("plan_summary", "")
        response = f"📋 已为你生成训练计划！\n\n{summary}\n\n"

        # Try to get plan_data for detailed output
        try:
            from app.services.plan_service import get_plan_by_id
            saved_plan = await get_plan_by_id(db, plan_id) if plan_id else None
            if saved_plan and saved_plan.plan_data:
                weekly_schedule = saved_plan.plan_data.get("weekly_schedule", [])
                for day in weekly_schedule:
                    response += f"【{day.get('day', '?')}】{day.get('focus', '')}\n"
                    for ex in day.get("exercises", []):
                        response += f"  • {ex.get('name', '?')} {ex.get('sets', '?')}组×{ex.get('reps', '?')}次\n"
                    if day.get("cardio"):
                        response += f"  有氧：{day['cardio']}\n"
                    response += f"  预计时长：{day.get('total_duration_min', '?')}分钟\n\n"
        except Exception:
            pass

        # Reminder status
        if reminder_result and reminder_result.get("success"):
            job_count = reminder_result.get("result", {}).get("job_count", 0)
            response += f"✅ 已创建 {job_count} 条每周训练提醒。"
        elif reminder_result:
            response += "⚠️ 训练计划已生成，但提醒创建遇到问题。你可以之后重新创建提醒。"
        else:
            response += "⚠️ 提醒未创建。你可以在设置中手动创建训练提醒。"
    else:
        response = "训练计划生成状态未知，请稍后查询或重试。"

    return {
        "observation_passed": passed,
        "observation_errors": observation_errors,
        "final_response": response,
    }


# =========================================================================
# Replan Node (Phase 2B Step 2)
# =========================================================================


def replan_node(state: AgentState) -> dict:
    """
    Replan Node: determine the next action when Observe fails.

    In:  state.observation_passed, state.observation_errors, state.tool_results,
         state.replan_count, state.user_profile
    Out: state.replan_action, state.replan_reason, state.replan_count

    Four action types (WHY only these four):
      - request_input:  profile incomplete — must ask user, cannot auto-fix
      - retry_once:     tool execution failed — worth one retry (transient errors)
      - simple_fix:     trivial parameter errors — safe to auto-correct
      - graceful_fail:  retry exhausted or unfixable problem — fail gracefully

    Boundary rules:
      - NEVER auto-escalate training intensity (safety risk)
      - NEVER modify user's stored profile (only fix in-memory params this run)
      - Reminder failures are NOT sent to retry (non-critical — plan is saved)
    """
    observation_errors = state.get("observation_errors", [])
    tool_results = state.get("tool_results", [])
    user_profile = state.get("user_profile", {})
    replan_count = state.get("replan_count", 0)

    # ---- Check: already exceeded max replans ----
    if replan_count > MAX_REPLANS:
        return {
            "replan_action": "graceful_fail",
            "replan_reason": f"replan_count_exceeded ({replan_count} > {MAX_REPLANS})",
            "replan_count": replan_count,
            "observation_passed": False,
            "final_response": (
                "系统多次尝试后仍无法完成训练计划生成。\n\n"
                "可能的原因：\n"
                "  • 个人信息格式有误，请检查并重新填写\n"
                "  • 系统暂时繁忙，请稍后重试\n\n"
                "如果问题持续，请联系管理员。"
            ),
        }

    # ---- Check 1: profile missing → request_input ----
    profile_errors = [e for e in observation_errors if "user_profile_not_found" in e or "missing_fields" in e]
    if profile_errors:
        return {
            "replan_action": "request_input",
            "replan_reason": "missing_required_profile_fields",
            "replan_count": replan_count,
            "observation_passed": False,
        }

    # ---- Check 2: tool failures → retry_once or graceful_fail ----
    tool_errors = [e for e in observation_errors if "generate_training_plan" in e or "create_weekly_reminder" in e or "not executed" in e or "plan_id missing" in e or "plan_data is empty" in e]
    # Filter out non-critical reminder warnings
    critical_tool_errors = [e for e in tool_errors if "plan saved" not in e and "(plan saved" not in e]

    if critical_tool_errors:
        if replan_count < MAX_REPLANS:
            return {
                "replan_action": "retry_once",
                "replan_reason": f"tool_execution_failed: {critical_tool_errors[0][:80]}",
                "replan_count": replan_count + 1,
                "observation_passed": False,
            }
        else:
            # Retry already exhausted
            return {
                "replan_action": "graceful_fail",
                "replan_reason": f"retry_exhausted: {critical_tool_errors[0][:80]}",
                "replan_count": replan_count,
                "observation_passed": False,
                "final_response": (
                    "训练计划生成失败，已尝试重新执行但仍未成功。\n\n"
                    f"失败原因：{critical_tool_errors[0]}\n\n"
                    "请检查你的个人信息是否正确，然后重新尝试。如果问题持续，请联系管理员。"
                ),
            }

    # ---- Check 3: simple parameter fix ----
    param_errors = [e for e in observation_errors if "weekly_days" in e or "preferred_time" in e or "count mismatch" in e]
    if param_errors:
        return {
            "replan_action": "simple_fix",
            "replan_reason": f"parameter_fix: {param_errors[0][:80]}",
            "replan_count": replan_count,
            "observation_passed": False,
        }

    # ---- Default: should not reach here, fallback to graceful_fail ----
    return {
        "replan_action": "graceful_fail",
        "replan_reason": "unknown_replan_trigger",
        "replan_count": replan_count,
        "observation_passed": False,
        "final_response": "训练计划生成过程中出现未知问题。请稍后重试。",
    }


def apply_simple_fix(state: dict, replan_reason: str) -> dict:
    """
    Apply trivial parameter fixes before retrying execution.

    Fixes applied (WHY these are safe):
      - weekly_days < 1  → 1    (must have at least 1 training day)
      - weekly_days > 7  → 7    (max 7 days in a week)
      - preferred_time missing → "19:00"  (reasonable default, evening workout)

    These are in-memory fixes only — the user's stored profile is NOT modified.
    The fixed values apply only for this execution cycle.
    """
    user_profile = state.get("user_profile", {}).copy()
    fixes_applied = []

    weekly_days = user_profile.get("weekly_days")
    if weekly_days is not None:
        weekly_days = int(weekly_days)
        if weekly_days < 1:
            user_profile["weekly_days"] = 1
            fixes_applied.append(f"weekly_days: {weekly_days} → 1")
        elif weekly_days > 7:
            user_profile["weekly_days"] = 7
            fixes_applied.append(f"weekly_days: {weekly_days} → 7")

    preferred_time = user_profile.get("preferred_time")
    if not preferred_time or preferred_time == "":
        user_profile["preferred_time"] = "19:00"
        fixes_applied.append("preferred_time: missing → 19:00")

    return {
        "user_profile": user_profile,
        "replan_reason": f"simple_fix applied: {'; '.join(fixes_applied)}",
    }


# =========================================================================
# Routing functions
# =========================================================================


def route_after_observe(state: AgentState) -> str:
    """
    Route after Observe: success → END, failure → REPLAN.

    Returns: "success" | "replan"
    """
    if state.get("observation_passed"):
        return "success"
    return "replan"


def route_after_replan(state: AgentState) -> str:
    """
    Route after Replan: determine next destination based on replan_action.

    Returns: "request_input" | "retry" | "fix" | "fail"
    """
    action = state.get("replan_action", "graceful_fail")
    if action == "request_input":
        return "request_input"
    elif action == "retry_once":
        return "retry"
    elif action == "simple_fix":
        return "fix"
    else:
        return "fail"


# =========================================================================
# PER Orchestrator — Plan → Execute → Observe → (Replan loop)
# =========================================================================

MAX_REPLAN_LOOPS = 2  # safety: prevent infinite loops


async def per_orchestrator_node(
    state: AgentState,
    db: AsyncSession,
    llm: Optional[LLMClient] = None,
) -> dict:
    """
    Orchestrate Plan → Execute → Observe → Replan for create_plan.

    The orchestrator runs in a loop, allowing retry and fix cycles.
    A safety counter (MAX_REPLAN_LOOPS) prevents infinite loops.

    Flow:
      Plan → [fail?] → Replan → [request_input?] → return to user
              ↓ pass
      Execute → Observe → [pass?] → return success
                          [fail?] → Replan
                                    → [retry] → loop back to Execute
                                    → [fix]   → loop back to Plan (with fixes)
                                    → [fail]  → return to user

    Returns:
      dict with: final_response, intent, plan_steps, tool_results,
                 tools_called, observation_passed, observation_errors,
                 replan_action, replan_reason, replan_count
    """
    merged = dict(state)  # mutable working copy
    merged["replan_count"] = merged.get("replan_count", 0)
    merged["replan_action"] = ""
    merged["replan_reason"] = ""
    loop_count = 0

    # ---- Phase 1: Plan ----
    plan_updates = await plan_node(merged, llm)

    # ---- Phase 1b: HITL Confirmation Gate (Phase 2C Step 2) ----
    # If Plan requires confirmation and user hasn't confirmed yet,
    # save state and return — execution pauses here.
    if plan_updates.get("requires_confirmation") and not state.get("confirmed"):
        merged.update(plan_updates)
        merged["confirmed"] = None  # waiting for user response
        return {
            "final_response": "",
            "intent": "create_plan",
            "plan_steps": plan_updates.get("plan_steps", []),
            "tool_results": [],
            "tools_called": [],
            "observation_passed": True,
            "observation_errors": [],
            "requires_confirmation": True,
            "confirmation_target": plan_updates.get("confirmation_target", ""),
            "confirmation_context": plan_updates.get("confirmation_context", {}),
            "_pending_state": merged,  # saved state for later recovery
        }

    # If user already confirmed, proceed normally
    if plan_updates.get("requires_confirmation") and state.get("confirmed"):
        # User confirmed — bypass the confirmation gate
        pass

    if not plan_updates.get("observation_passed"):
        # Plan failed → Replan to determine action
        merged.update(plan_updates)
        replan_updates = replan_node(merged)
        merged.update(replan_updates)

        if merged.get("replan_action") == "request_input":
            # Return to user with the Plan node's error message (what's missing)
            return _build_result(merged, plan_updates)

        # Any other replan action on Plan failure → graceful_fail for now
        # (Plan failures are always "missing info" — cannot retry/fix)
        return _build_result(merged, plan_updates)

    merged.update(plan_updates)

    # ---- Main PER loop ----
    while loop_count < MAX_REPLAN_LOOPS:
        loop_count += 1

        # ---- Phase 2: Execute ----
        exec_updates = await execute_node(merged, db, llm)
        merged.update(exec_updates)

        # ---- Phase 3: Observe ----
        obs_updates = await observe_node(merged, db)
        merged.update(obs_updates)

        # ---- Check: passed? ----
        if merged.get("observation_passed"):
            # Success — Replan may still flag non-critical warnings
            merged["replan_action"] = "success"
            merged["replan_reason"] = ""
            return _build_result(merged, obs_updates)

        # ---- Phase 4: Replan ----
        replan_updates = replan_node(merged)
        merged.update(replan_updates)

        action = merged.get("replan_action", "graceful_fail")

        if action == "retry_once":
            # Go back to Execute (loop continues)
            merged["observation_errors"] = []
            continue

        elif action == "simple_fix":
            # Apply fixes and go back to Plan → Execute
            fix_updates = apply_simple_fix(merged, merged.get("replan_reason", ""))
            merged.update(fix_updates)
            # Re-run Plan with fixed params
            plan_updates = await plan_node(merged, llm)
            if not plan_updates.get("observation_passed"):
                merged.update(plan_updates)
                merged["replan_action"] = "graceful_fail"
                merged["replan_reason"] = "fix_failed_plan_validation"
                return _build_result(merged, plan_updates)
            merged.update(plan_updates)
            continue

        elif action == "request_input":
            # Return Plan node's message about missing info
            return _build_result(merged, plan_updates)

        else:
            # graceful_fail or unknown
            return _build_result(merged, {})

    # Safety: loop exhausted
    merged["replan_action"] = "graceful_fail"
    merged["replan_reason"] = "max_loop_exceeded"
    merged["final_response"] = "系统处理超时，请稍后重试。"
    return _build_result(merged, {})


def _build_result(merged: dict, obs_or_plan: dict) -> dict:
    """Build the standardized result dict for the orchestrator."""
    # Build Replan info for trace
    replan_info = {}
    if merged.get("replan_action") and merged.get("replan_action") != "success":
        replan_info = {
            "replan_action": merged.get("replan_action"),
            "replan_reason": merged.get("replan_reason"),
            "replan_count": merged.get("replan_count", 0),
        }

    return {
        "final_response": merged.get("final_response", obs_or_plan.get("final_response", "")),
        "intent": "create_plan",
        "plan_steps": merged.get("plan_steps", []),
        "tool_results": merged.get("tool_results", []),
        "tools_called": merged.get("tools_called", []),
        "observation_passed": merged.get("observation_passed", False),
        "observation_errors": merged.get("observation_errors", []),
        "requires_confirmation": False,
        **replan_info,
    }
