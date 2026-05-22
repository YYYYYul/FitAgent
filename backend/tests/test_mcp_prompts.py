"""Tests for MCP Prompts (Phase 3B Step 4)."""

import pytest
from app.mcp.prompts import list_prompts, get_prompt


class TestPromptRegistry:
    """Verify prompt registration and listing."""

    def test_list_5_prompts(self):
        prompts = list_prompts()
        assert len(prompts) == 5
        names = [p["name"] for p in prompts]
        assert "create-fitness-plan" in names
        assert "weekly-review" in names
        assert "monthly-summary-analysis" in names
        assert "workout-consistency-check" in names
        assert "beginner-guidance" in names

    def test_each_prompt_has_required_fields(self):
        for p in list_prompts():
            assert "name" in p
            assert "description" in p
            assert "category" in p
            assert "version" in p
            assert "arguments" in p

    def test_prompt_categories(self):
        prompts = list_prompts()
        categories = {p["category"] for p in prompts}
        assert "planning" in categories
        assert "review" in categories
        assert "analysis" in categories
        assert "guidance" in categories

    def test_unknown_prompt_returns_error(self):
        result = get_prompt("nonexistent-prompt")
        assert result["success"] is False
        assert "Unknown prompt" in result["error"]


class TestPromptGet:
    """Verify individual prompt retrieval."""

    def test_create_fitness_plan_has_workflow(self):
        result = get_prompt("create-fitness-plan")
        assert result["success"] is True
        p = result["prompt"]
        assert p["category"] == "planning"
        assert len(p["workflow"]["steps"]) == 4
        assert "messages" in p

    def test_create_fitness_plan_has_messages(self):
        result = get_prompt("create-fitness-plan", {"goal": "fat_loss"})
        assert len(result["prompt"]["messages"]) == 2
        system_msg = result["prompt"]["messages"][0]
        assert system_msg["role"] == "system"
        user_msg = result["prompt"]["messages"][1]
        assert user_msg["role"] == "user"
        assert "fat_loss" in user_msg["content"]["text"]

    def test_weekly_review_has_workflow(self):
        result = get_prompt("weekly-review")
        assert result["success"] is True
        steps = result["prompt"]["workflow"]["steps"]
        assert len(steps) == 3
        # Step 1 should be a resource read
        assert steps[0]["action"] == "read_resource"

    def test_monthly_summary_has_workflow(self):
        result = get_prompt("monthly-summary-analysis")
        assert result["success"] is True
        assert result["prompt"]["category"] == "review"

    def test_workout_consistency_has_workflow(self):
        result = get_prompt("workout-consistency-check")
        assert result["success"] is True
        steps = result["prompt"]["workflow"]["steps"]
        # Should have analysis step
        actions = [s["action"] for s in steps]
        assert "analysis" in actions

    def test_beginner_guidance_references_tool(self):
        result = get_prompt("beginner-guidance", {"topic": "第一次去健身房"})
        assert result["success"] is True
        steps = result["prompt"]["workflow"]["steps"]
        # Step 1 should call search_fitness_knowledge
        assert steps[0]["action"] == "call_tool"
        assert steps[0]["tool"] == "search_fitness_knowledge"

    def test_prompt_messages_include_template(self):
        result = get_prompt("monthly-summary-analysis", {"year": "2026", "month": "6"})
        user_msg = result["prompt"]["messages"][1]
        assert "2026" in user_msg["content"]["text"]
        assert "monthly-summary-analysis" in user_msg["content"]["text"]


class TestMCPServerPrompts:
    """Verify MCP server handles prompt methods correctly."""

    def test_handle_prompts_list(self):
        from app.mcp.server import process_message
        import asyncio
        async def _run():
            msg = {"jsonrpc": "2.0", "id": 20, "method": "prompts/list", "params": {}}
            return await process_message(msg)
        resp = asyncio.run(_run())
        assert "prompts" in resp["result"]

    def test_handle_prompts_get_success(self):
        from app.mcp.server import process_message
        import asyncio
        async def _run():
            msg = {"jsonrpc": "2.0", "id": 21, "method": "prompts/get",
                   "params": {"name": "beginner-guidance"}}
            return await process_message(msg)
        resp = asyncio.run(_run())
        assert "messages" in resp["result"]

    def test_handle_prompts_get_unknown(self):
        from app.mcp.server import process_message
        import asyncio
        async def _run():
            msg = {"jsonrpc": "2.0", "id": 22, "method": "prompts/get",
                   "params": {"name": "unknown"}}
            return await process_message(msg)
        resp = asyncio.run(_run())
        assert "error" in resp

    def test_initialize_includes_prompts(self):
        from app.mcp.server import handle_initialize
        result = handle_initialize({})
        assert "prompts" in result["capabilities"]
