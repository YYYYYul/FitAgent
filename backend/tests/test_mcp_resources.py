"""Tests for MCP Resources (Phase 3B Step 3)."""

import pytest
import asyncio
from app.mcp.resources import list_resources, read_resource

# Module-level test user cache
_RES_USER_ID = None


async def _get_test_user_id() -> str:
    """Get or create a test user for resource tests."""
    global _RES_USER_ID
    if _RES_USER_ID:
        return _RES_USER_ID
    from app.db.session import AsyncSessionLocal
    from app.models.user import UserProfile
    from sqlalchemy import select
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserProfile).limit(1))
        user = result.scalar_one_or_none()
        if user:
            _RES_USER_ID = str(user.id)
        else:
            import uuid
            from app.services.user_service import register_user
            user = await register_user(db, "res-test@fitagent.dev", "test12345", "Res Test")
            await db.commit()
            _RES_USER_ID = str(user.id)
    return _RES_USER_ID


class TestResourceRegistry:
    """Verify resource registration and listing."""

    def test_list_4_resources(self):
        resources = list_resources()
        assert len(resources) == 4
        uris = [r["uri"] for r in resources]
        assert "fitness://active-plan" in uris
        assert "fitness://monthly-summary" in uris
        assert "fitness://history/latest" in uris
        assert "fitness://reminders/status" in uris

    def test_each_resource_has_required_fields(self):
        for r in list_resources():
            assert "uri" in r
            assert "name" in r
            assert "description" in r
            assert "mimeType" in r

    def test_all_resources_use_fitness_scheme(self):
        for r in list_resources():
            assert r["uri"].startswith("fitness://")


class TestResourceRead:
    """Verify resource read operations with a test user."""

    @pytest.mark.asyncio
    async def test_unknown_resource(self):
        result = await read_resource("fitness://nonexistent")
        assert result["success"] is False
        assert "Unknown resource" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_scheme(self):
        result = await read_resource("http://active-plan")
        assert result["success"] is False
        assert "Unsupported scheme" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_uri(self):
        result = await read_resource("not-a-uri")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_active_plan_missing_user_id(self):
        result = await read_resource("fitness://active-plan")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_active_plan_returns_data(self):
        uid = await _get_test_user_id()
        result = await read_resource(f"fitness://active-plan?user_id={uid}")
        assert result["success"] is True
        assert "data" in result

    @pytest.mark.asyncio
    async def test_monthly_summary_valid(self):
        uid = await _get_test_user_id()
        result = await read_resource(f"fitness://monthly-summary?user_id={uid}&year=2026&month=5")
        assert result["success"] is True
        data = result["data"]
        assert "completed_days" in data
        assert "completion_rate" in data

    @pytest.mark.asyncio
    async def test_monthly_summary_invalid_month(self):
        uid = await _get_test_user_id()
        result = await read_resource(f"fitness://monthly-summary?user_id={uid}&year=2026&month=13")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_monthly_summary_missing_user_id(self):
        result = await read_resource("fitness://monthly-summary?year=2026&month=5")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_history_latest_returns_records(self):
        uid = await _get_test_user_id()
        result = await read_resource(f"fitness://history/latest?user_id={uid}&limit=5")
        assert result["success"] is True
        assert "records" in result["data"]

    @pytest.mark.asyncio
    async def test_history_latest_clamps_limit(self):
        uid = await _get_test_user_id()
        result = await read_resource(f"fitness://history/latest?user_id={uid}&limit=999")
        assert result["success"] is True
        assert result["data"]["count"] <= 50

    @pytest.mark.asyncio
    async def test_history_latest_missing_user_id(self):
        result = await read_resource("fitness://history/latest")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_reminders_status_returns_data(self):
        uid = await _get_test_user_id()
        result = await read_resource(f"fitness://reminders/status?user_id={uid}")
        assert result["success"] is True
        data = result["data"]
        assert "active_jobs" in data
        assert "scheduler_running" in data

    @pytest.mark.asyncio
    async def test_reminders_status_missing_user_id(self):
        result = await read_resource("fitness://reminders/status")
        assert result["success"] is False


class TestMCPServerResources:
    """Verify MCP server handles resource methods correctly."""

    def test_handle_resources_list(self):
        from app.mcp.server import handle_resources_list
        result = handle_resources_list({})
        assert "resources" in result
        assert len(result["resources"]) == 4

    @pytest.mark.asyncio
    async def test_process_resources_list(self):
        from app.mcp.server import process_message
        msg = {"jsonrpc": "2.0", "id": 10, "method": "resources/list", "params": {}}
        resp = await process_message(msg)
        assert resp["result"]["resources"][0]["uri"].startswith("fitness://")

    @pytest.mark.asyncio
    async def test_process_resources_read(self):
        from app.mcp.server import process_message
        msg = {
            "jsonrpc": "2.0", "id": 11, "method": "resources/read",
            "params": {"uri": "fitness://active-plan?user_id=test"},
        }
        resp = await process_message(msg)
        assert "contents" in resp["result"]

    def test_initialize_includes_resources(self):
        from app.mcp.server import handle_initialize
        result = handle_initialize({})
        assert "resources" in result["capabilities"]
