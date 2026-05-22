"""Tests for Plan-Execute-Observe-Replan subgraph (Phase 2B Step 2)."""

import pytest
from app.core.agent.nodes.per_subgraph import (
    plan_node,
    observe_node,
    replan_node,
    apply_simple_fix,
    route_after_observe,
    route_after_replan,
    per_orchestrator_node,
    MAX_REPLANS,
)


# =========================================================================
# Plan Node tests (Step 1 — unchanged)
# =========================================================================


class TestPlanNode:
    @pytest.mark.asyncio
    async def test_plan_passes_with_complete_profile(self):
        state = {
            "user_input": "帮我制定训练计划",
            "user_profile": {
                "goal": "fat_loss", "height_cm": 175, "weight_kg": 80,
                "training_location": "gym", "weekly_days": 4,
                "experience_level": "intermediate", "preferred_time": "19:00",
            },
        }
        result = await plan_node(state)
        assert result["observation_passed"] is True
        assert result["plan_steps"] == ["generate_training_plan", "create_weekly_reminder"]

    @pytest.mark.asyncio
    async def test_plan_fails_with_no_profile(self):
        state = {"user_input": "plan", "user_profile": None}
        result = await plan_node(state)
        assert result["observation_passed"] is False
        assert "user_profile_not_found" in result["observation_errors"]

    @pytest.mark.asyncio
    async def test_plan_fails_with_missing_fields(self):
        state = {"user_input": "plan", "user_profile": {"goal": "health"}}
        result = await plan_node(state)
        assert result["observation_passed"] is False
        assert "missing_fields" in result["observation_errors"][0]

    @pytest.mark.asyncio
    async def test_plan_reports_missing_field_labels(self):
        state = {
            "user_input": "plan",
            "user_profile": {"goal": "muscle_gain", "height_cm": 180},
        }
        result = await plan_node(state)
        msg = result["final_response"]
        assert "体重" in msg and "训练地点" in msg and "每周训练天数" in msg and "训练经验" in msg


# =========================================================================
# Observe Node tests (Step 1 — unchanged)
# =========================================================================


class TestObserveNode:
    @pytest.mark.asyncio
    async def test_observe_fails_with_no_plan(self):
        result = await observe_node({"tool_results": [], "user_profile": {"weekly_days": 4}}, db=None)
        assert result["observation_passed"] is False

    @pytest.mark.asyncio
    async def test_observe_fails_with_failed_plan(self):
        result = await observe_node({
            "tool_results": [{"step": "generate_training_plan", "tool": "generate_training_plan", "success": False, "error": "bad"}],
            "user_profile": {"weekly_days": 4},
        }, db=None)
        assert result["observation_passed"] is False


# =========================================================================
# Replan Node tests (Step 2 — new)
# =========================================================================


class TestReplanNode:
    """Verify Replan Node: action determination from observation_errors."""

    def test_request_input_for_missing_profile(self):
        """Profile missing → request_input."""
        state = {
            "observation_passed": False,
            "observation_errors": ["user_profile_not_found"],
            "tool_results": [],
            "replan_count": 0,
        }
        result = replan_node(state)
        assert result["replan_action"] == "request_input"
        assert result["replan_reason"] == "missing_required_profile_fields"

    def test_request_input_for_missing_fields(self):
        """Profile fields missing → request_input."""
        state = {
            "observation_passed": False,
            "observation_errors": ["missing_fields: goal,height_cm"],
            "tool_results": [],
            "replan_count": 0,
        }
        result = replan_node(state)
        assert result["replan_action"] == "request_input"

    def test_retry_once_for_tool_failure(self):
        """Tool failure with retries remaining → retry_once."""
        state = {
            "observation_passed": False,
            "observation_errors": ["generate_training_plan: invalid_params"],
            "tool_results": [{"tool": "generate_training_plan", "success": False}],
            "replan_count": 0,
        }
        result = replan_node(state)
        assert result["replan_action"] == "retry_once"
        assert result["replan_count"] == 1

    def test_graceful_fail_when_retry_exhausted(self):
        """Tool failure with retry count >= MAX → graceful_fail."""
        state = {
            "observation_passed": False,
            "observation_errors": ["generate_training_plan: failed again"],
            "tool_results": [{"tool": "generate_training_plan", "success": False}],
            "replan_count": MAX_REPLANS + 1,  # exhausted
        }
        result = replan_node(state)
        assert result["replan_action"] == "graceful_fail"

    def test_graceful_fail_when_count_exceeded(self):
        """replan_count exceeds MAX_REPLANS directly → graceful_fail."""
        state = {
            "observation_passed": False,
            "observation_errors": [],
            "tool_results": [],
            "replan_count": 99,
        }
        result = replan_node(state)
        assert result["replan_action"] == "graceful_fail"
        assert "replan_count_exceeded" in result["replan_reason"]

    def test_simple_fix_for_param_errors(self):
        """Parameter errors → simple_fix."""
        state = {
            "observation_passed": False,
            "observation_errors": ["reminder_job count mismatch: expected 4, got 2"],
            "tool_results": [{"tool": "create_weekly_reminder", "success": True, "result": {"job_count": 2}}],
            "replan_count": 0,
        }
        result = replan_node(state)
        assert result["replan_action"] == "simple_fix"

    def test_reminder_non_critical_not_retried(self):
        """Reminder-only failure → NOT retried (non-critical), falls through."""
        state = {
            "observation_passed": True,  # plan succeeded
            "observation_errors": ["create_weekly_reminder: failed (plan saved, reminders can be recreated)"],
            "tool_results": [
                {"tool": "generate_training_plan", "success": True, "result": {"plan_id": "x"}},
                {"tool": "create_weekly_reminder", "success": False},
            ],
            "replan_count": 0,
        }
        result = replan_node(state)
        # Reminder failure treated as non-critical → should NOT trigger retry
        assert result["replan_action"] != "retry_once"


# =========================================================================
# Simple Fix tests (Step 2 — new)
# =========================================================================


class TestSimpleFix:
    """Verify apply_simple_fix: trivial parameter corrections."""

    def test_fix_weekly_days_too_high(self):
        state = {"user_profile": {"weekly_days": 10, "preferred_time": "19:00"}}
        result = apply_simple_fix(state, "test")
        assert result["user_profile"]["weekly_days"] == 7
        assert "weekly_days: 10 → 7" in result["replan_reason"]

    def test_fix_weekly_days_too_low(self):
        state = {"user_profile": {"weekly_days": 0, "preferred_time": "19:00"}}
        result = apply_simple_fix(state, "test")
        assert result["user_profile"]["weekly_days"] == 1

    def test_fix_missing_preferred_time(self):
        state = {"user_profile": {"weekly_days": 4, "preferred_time": ""}}
        result = apply_simple_fix(state, "test")
        assert result["user_profile"]["preferred_time"] == "19:00"

    def test_fix_does_not_change_stored_profile(self):
        """The fix only modifies the in-memory copy, not the original."""
        original = {"weekly_days": 10, "preferred_time": None}
        state = {"user_profile": original.copy()}
        result = apply_simple_fix(state, "test")
        assert result["user_profile"]["weekly_days"] == 7
        assert original["weekly_days"] == 10  # unchanged


# =========================================================================
# Routing tests (Step 2 — new)
# =========================================================================


class TestRouting:
    """Verify route_after_observe and route_after_replan."""

    def test_route_after_observe_success(self):
        assert route_after_observe({"observation_passed": True}) == "success"

    def test_route_after_observe_failure(self):
        assert route_after_observe({"observation_passed": False}) == "replan"

    def test_route_after_replan_request_input(self):
        assert route_after_replan({"replan_action": "request_input"}) == "request_input"

    def test_route_after_replan_retry(self):
        assert route_after_replan({"replan_action": "retry_once"}) == "retry"

    def test_route_after_replan_fix(self):
        assert route_after_replan({"replan_action": "simple_fix"}) == "fix"

    def test_route_after_replan_fail(self):
        assert route_after_replan({"replan_action": "graceful_fail"}) == "fail"

    def test_route_after_replan_unknown_defaults_to_fail(self):
        assert route_after_replan({"replan_action": "unknown"}) == "fail"


# =========================================================================
# Integration tests (Step 2 — new)
# =========================================================================


class TestPERIntegration:
    """End-to-end PER orchestrator tests."""

    @pytest.mark.asyncio
    async def test_per_early_exit_on_no_profile(self):
        """No profile → Plan fails → request_input → early return."""
        state = _make_state(user_profile=None)
        result = await per_orchestrator_node(state, db=None, llm=None)
        assert result["observation_passed"] is False
        assert result["tools_called"] == []
        assert "user_profile_not_found" in str(result.get("observation_errors", []))

    @pytest.mark.asyncio
    async def test_per_returns_replan_info_on_failure(self):
        """Failed plan includes replan action and reason in result."""
        state = _make_state(user_profile={"goal": "health"})  # incomplete
        result = await per_orchestrator_node(state, db=None, llm=None)
        assert "replan_action" in result
        assert "replan_reason" in result
        assert result["replan_action"] in ("request_input", "graceful_fail")


def _make_state(**overrides) -> dict:
    """Helper: build a minimal AgentState-like dict for testing."""
    base = {
        "user_input": "test plan request",
        "user_id": "test-user-1",
        "user_profile": None,
        "plan_steps": [],
        "current_step": 0,
        "tool_results": [],
        "observation_passed": True,
        "observation_errors": [],
        "replan_count": 0,
        "replan_reason": None,
        "tools_called": [],
    }
    base.update(overrides)
    return base
