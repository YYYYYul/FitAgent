"""Tests for MCP Server — all 4 tools + registry + protocol (Phase 3B Step 2)."""

import pytest
import asyncio
from app.mcp.tools import list_tools, call_tool


# Test user fixture — ensures a valid user exists for FK constraints
_TEST_USER_ID = None


async def _ensure_test_user() -> str:
    """Get or create a test user for FK-dependent tests."""
    global _TEST_USER_ID
    if _TEST_USER_ID:
        return _TEST_USER_ID
    from app.db.session import AsyncSessionLocal
    from app.models.user import UserProfile
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserProfile).limit(1))
        user = result.scalar_one_or_none()
        if user:
            _TEST_USER_ID = str(user.id)
        else:
            import uuid
            from app.services.user_service import register_user
            user = await register_user(db, "mcp-test@fitagent.dev", "test12345", "MCP Test")
            await db.commit()
            _TEST_USER_ID = str(user.id)
    return _TEST_USER_ID


# =========================================================================
# Tool Registry
# =========================================================================


class TestMCPToolRegistry:
    """Verify all 4 tools are registered and routable."""

    def test_list_4_tools(self):
        tools = list_tools()
        assert len(tools) == 4
        names = [t["name"] for t in tools]
        assert "generate_training_plan" in names
        assert "log_workout_record" in names
        assert "search_fitness_knowledge" in names
        assert "create_weekly_reminder" in names

    def test_each_tool_has_schema(self):
        for tool in list_tools():
            assert "inputSchema" in tool
            assert "description" in tool
            assert len(tool["description"]) > 20

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self):
        result = await call_tool("nonexistent", {})
        assert result["success"] is False
        assert "Unknown tool" in result["error"]


# =========================================================================
# Tool 1: generate_training_plan
# =========================================================================


class TestMCPGeneratePlan:
    @pytest.mark.asyncio
    async def test_valid_call(self):
        result = await call_tool("generate_training_plan", {
            "goal": "fat_loss", "height_cm": 175, "weight_kg": 80,
            "training_location": "gym", "weekly_days": 4,
            "experience_level": "intermediate",
        })
        assert result["success"] is True
        assert result["source"] == "mcp"
        assert len(result["weekly_schedule"]) == 4

    @pytest.mark.asyncio
    async def test_missing_required(self):
        result = await call_tool("generate_training_plan", {"goal": "health"})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_invalid_goal(self):
        result = await call_tool("generate_training_plan", {
            "goal": "invalid", "height_cm": 175, "weight_kg": 80,
            "training_location": "gym", "weekly_days": 4,
            "experience_level": "intermediate",
        })
        assert result["success"] is False
        assert "goal" in result["error"].lower()


# =========================================================================
# Tool 2: log_workout_record
# =========================================================================


class TestMCPLogWorkout:
    @pytest.mark.asyncio
    async def test_valid_call(self):
        uid = await _ensure_test_user()
        result = await call_tool("log_workout_record", {
            "user_id": uid,
            "raw_text": "练了胸，卧推60kg 5x5，飞鸟12kg 3x12",
        })
        assert result["success"] is True
        assert result["source"] == "mcp"
        assert result["log_id"] is not None

    @pytest.mark.asyncio
    async def test_missing_raw_text(self):
        uid = await _ensure_test_user()
        result = await call_tool("log_workout_record", {"user_id": uid})
        assert result["success"] is False
        assert "raw_text" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_user_id(self):
        result = await call_tool("log_workout_record", {"raw_text": "test"})
        assert result["success"] is False
        assert "user_id" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_with_date(self):
        uid = await _ensure_test_user()
        result = await call_tool("log_workout_record", {
            "user_id": uid, "raw_text": "深蹲100kg 5x5", "date": "2026-05-15",
        })
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_invalid_date(self):
        uid = await _ensure_test_user()
        result = await call_tool("log_workout_record", {
            "user_id": uid, "raw_text": "test", "date": "not-a-date",
        })
        assert result["success"] is False
        assert "date" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_empty_raw_text(self):
        uid = await _ensure_test_user()
        result = await call_tool("log_workout_record", {"user_id": uid, "raw_text": "   "})
        assert result["success"] is False


# =========================================================================
# Tool 3: search_fitness_knowledge (RAG)
# =========================================================================


class TestMCPSearchKnowledge:
    @pytest.mark.asyncio
    async def test_valid_search(self):
        result = await call_tool("search_fitness_knowledge", {
            "query": "新手应该怎么开始健身",
        })
        assert result["success"] is True
        assert result["source"] == "mcp"
        assert result["result_count"] >= 1
        assert len(result["results"]) >= 1
        first = result["results"][0]
        assert "title" in first
        assert "content" in first
        assert "category" in first
        assert "score" in first

    @pytest.mark.asyncio
    async def test_search_with_top_k(self):
        result = await call_tool("search_fitness_knowledge", {
            "query": "减脂", "top_k": 2,
        })
        assert result["success"] is True
        assert result["result_count"] <= 2

    @pytest.mark.asyncio
    async def test_missing_query(self):
        result = await call_tool("search_fitness_knowledge", {})
        assert result["success"] is False
        assert "query" in result["error"]

    @pytest.mark.asyncio
    async def test_empty_query(self):
        result = await call_tool("search_fitness_knowledge", {"query": "  "})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_search_returns_relevant_results(self):
        result = await call_tool("search_fitness_knowledge", {
            "query": "减脂应该做什么训练",
        })
        assert result["success"] is True
        # At least one result should be about fat_loss
        categories = [r["category"] for r in result["results"]]
        assert any("fat_loss" in c for c in categories)


# =========================================================================
# Tool 4: create_weekly_reminder
# =========================================================================


class TestMCPCreateReminder:
    @pytest.mark.asyncio
    async def test_valid_call(self):
        result = await call_tool("create_weekly_reminder", {
            "user_id": "test-user-mcp",
            "plan_id": "test-plan-mcp",
            "training_days": [
                {"day_of_week": 0, "remind_time": "19:00"},
                {"day_of_week": 2, "remind_time": "19:00"},
            ],
        })
        assert result["success"] is True
        assert result["source"] == "mcp"
        assert len(result["reminder_jobs"]) == 2
        assert "scheduler_status" in result

    @pytest.mark.asyncio
    async def test_missing_user_id(self):
        result = await call_tool("create_weekly_reminder", {
            "plan_id": "x", "training_days": [{"day_of_week": 1, "remind_time": "08:00"}],
        })
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_invalid_day_of_week(self):
        result = await call_tool("create_weekly_reminder", {
            "user_id": "u1", "plan_id": "p1",
            "training_days": [{"day_of_week": 8, "remind_time": "19:00"}],
        })
        assert result["success"] is False
        assert "day_of_week" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_remind_time(self):
        result = await call_tool("create_weekly_reminder", {
            "user_id": "u1", "plan_id": "p1",
            "training_days": [{"day_of_week": 1, "remind_time": "25:00"}],
        })
        assert result["success"] is False
        assert "remind_time" in result["error"]

    @pytest.mark.asyncio
    async def test_empty_training_days(self):
        result = await call_tool("create_weekly_reminder", {
            "user_id": "u1", "plan_id": "p1", "training_days": [],
        })
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_training_days_not_list(self):
        result = await call_tool("create_weekly_reminder", {
            "user_id": "u1", "plan_id": "p1", "training_days": "not-a-list",
        })
        assert result["success"] is False


# =========================================================================
# MCP Server protocol (sync handlers only)
# =========================================================================


class TestMCPServerProtocol:
    def test_server_name(self):
        from app.mcp.server import SERVER_NAME
        assert SERVER_NAME == "FitAgent MCP Server"

    def test_handle_initialize(self):
        from app.mcp.server import handle_initialize
        result = handle_initialize({"clientInfo": {"name": "test"}})
        assert "tools" in result["capabilities"]
        assert result["protocolVersion"] == "2024-11-05"

    def test_handle_tools_list(self):
        from app.mcp.server import handle_tools_list
        result = handle_tools_list({})
        assert len(result["tools"]) == 4

    def test_rpc_response_format(self):
        from app.mcp.server import _rpc_response
        resp = _rpc_response({"id": 1}, {"k": "v"})
        assert resp["jsonrpc"] == "2.0"

    def test_error_response_format(self):
        from app.mcp.server import _error_response
        resp = _error_response({"id": 1}, -32601, "Not found")
        assert resp["error"]["code"] == -32601
