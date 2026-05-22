"""
MCP Resource registry for FitAgent (Phase 3B Step 3).

Resources expose read-only access to FitAgent's state data:
  - fitness://active-plan         — current active training plan
  - fitness://monthly-summary     — monthly workout statistics
  - fitness://history/latest      — recent workout records
  - fitness://reminders/status    — reminder scheduler status

WHY Resources vs Tools:
  Resources are for READING state (no side effects).
  Tools are for EXECUTING actions (create/update/delete).
  MCP Clients query Resources to understand context, then call Tools to act.

URI design:  fitness://{resource-path}?param1=val1&param2=val2
"""

from urllib.parse import urlparse, parse_qs
from app.db.session import AsyncSessionLocal
from app.services.plan_service import get_active_plan
from app.services.workout_service import get_workout_logs, get_monthly_summary
from app.core.reminder.scheduler import is_scheduler_running, get_registered_job_count


# =========================================================================
# Resource definitions
# =========================================================================

RESOURCE_DEFINITIONS = [
    {
        "uri": "fitness://active-plan",
        "name": "Active Training Plan",
        "description": "The currently active training plan for a user. Returns null if no active plan exists.",
        "mimeType": "application/json",
        "parameters": {"user_id": "string (required)"},
    },
    {
        "uri": "fitness://monthly-summary",
        "name": "Monthly Workout Summary",
        "description": "Monthly training statistics: completed days, completion rate, streak, duration, and focus distribution.",
        "mimeType": "application/json",
        "parameters": {"user_id": "string (required)", "year": "int", "month": "int"},
    },
    {
        "uri": "fitness://history/latest",
        "name": "Latest Workout History",
        "description": "Most recent workout records for a user, ordered by date descending.",
        "mimeType": "application/json",
        "parameters": {"user_id": "string (required)", "limit": "int (default 10, max 50)"},
    },
    {
        "uri": "fitness://reminders/status",
        "name": "Reminder Status",
        "description": "Current reminder scheduler status: active job count, scheduler health, and recent trigger events.",
        "mimeType": "application/json",
        "parameters": {"user_id": "string (required)"},
    },
]


# =========================================================================
# Public API
# =========================================================================


def list_resources() -> list[dict]:
    """Return all registered resource definitions (MCP resources/list response)."""
    return RESOURCE_DEFINITIONS


async def read_resource(uri: str) -> dict:
    """
    Read a resource by URI.

    Parses the URI, validates parameters, routes to the appropriate handler,
    and returns structured content.

    Returns:
        On success: {"success": true, "data": {...}, "uri": str}
        On error:   {"success": false, "error": str, "uri": str}
    """
    # Step 1: Parse URI
    try:
        parsed = urlparse(uri)
    except Exception:
        return {"success": False, "error": f"Invalid URI: {uri}", "uri": uri}

    scheme = parsed.scheme
    # For URIs like fitness://active-plan, the resource name is in netloc, not path.
    # For URIs like fitness://history/latest, netloc="history" and path="/latest".
    netloc = parsed.netloc
    path = parsed.path.strip("/")
    # Combine: netloc + "/" + path, strip trailing empty segments
    if path:
        resource_path = f"{netloc}/{path}"
    else:
        resource_path = netloc
    params = {k: v[0] for k, v in parse_qs(parsed.query).items()}

    if scheme != "fitness":
        return {"success": False, "error": f"Unsupported scheme: {scheme}. Only fitness:// is supported.", "uri": uri}

    # Step 2: Route to handler
    try:
        if resource_path == "active-plan":
            return await _handle_active_plan(params, uri)
        elif resource_path == "monthly-summary":
            return await _handle_monthly_summary(params, uri)
        elif resource_path == "history/latest":
            return await _handle_history_latest(params, uri)
        elif resource_path == "reminders/status":
            return await _handle_reminders_status(params, uri)
        else:
            return {"success": False, "error": f"Unknown resource: {resource_path}", "uri": uri}
    except Exception as e:
        return {"success": False, "error": f"Resource read failed: {str(e)}", "uri": uri}


# =========================================================================
# Resource handlers
# =========================================================================


async def _handle_active_plan(params: dict, uri: str) -> dict:
    """fitness://active-plan?user_id=xxx"""
    user_id = params.get("user_id", "").strip()
    if not user_id:
        return {"success": False, "error": "Missing required parameter: user_id", "uri": uri}

    async with AsyncSessionLocal() as db:
        plan = await get_active_plan(db, user_id)

    if not plan:
        return {
            "success": True,
            "data": None,
            "message": "No active training plan found for this user.",
            "uri": uri,
        }

    return {
        "success": True,
        "data": {
            "plan_id": str(plan.id),
            "goal": plan.goal,
            "weekly_days": plan.weekly_days,
            "plan_summary": plan.plan_summary,
            "weekly_schedule": plan.plan_data.get("weekly_schedule", []) if plan.plan_data else [],
            "version": plan.version,
            "status": plan.status,
            "updated_at": str(plan.updated_at),
        },
        "uri": uri,
    }


async def _handle_monthly_summary(params: dict, uri: str) -> dict:
    """fitness://monthly-summary?user_id=xxx&year=2026&month=5"""
    user_id = params.get("user_id", "").strip()
    if not user_id:
        return {"success": False, "error": "Missing required parameter: user_id", "uri": uri}

    try:
        year = int(params.get("year", 2026))
        month = int(params.get("month", 5))
        if not (1 <= month <= 12):
            raise ValueError
    except ValueError:
        return {"success": False, "error": "year and month must be valid integers (month 1-12)", "uri": uri}

    async with AsyncSessionLocal() as db:
        summary = await get_monthly_summary(db, user_id, year, month)
        # Calculate planned days from active plan
        plan = await get_active_plan(db, user_id)
        if plan and plan.plan_data:
            weekly_schedule = plan.plan_data.get("weekly_schedule", [])
            import calendar
            _, days_in_month = calendar.monthrange(year, month)
            planned_days = round(len(weekly_schedule) * days_in_month / 7)
        else:
            planned_days = summary["completed_days"]

    completion_rate = summary["completed_days"] / planned_days if planned_days > 0 else 0.0

    return {
        "success": True,
        "data": {
            "year": year,
            "month": month,
            "planned_days": planned_days,
            "completed_days": summary["completed_days"],
            "completion_rate": round(completion_rate, 2),
            "streak_days": summary["streak_days"],
            "total_duration_min": summary["total_duration_min"],
            "by_focus": summary["by_focus"],
        },
        "uri": uri,
    }


async def _handle_history_latest(params: dict, uri: str) -> dict:
    """fitness://history/latest?user_id=xxx&limit=10"""
    user_id = params.get("user_id", "").strip()
    if not user_id:
        return {"success": False, "error": "Missing required parameter: user_id", "uri": uri}

    try:
        limit = int(params.get("limit", 10))
        if limit < 1 or limit > 50:
            limit = 10
    except ValueError:
        limit = 10

    async with AsyncSessionLocal() as db:
        logs = await get_workout_logs(db, user_id, limit=limit)

    return {
        "success": True,
        "data": {
            "count": len(logs),
            "records": [
                {
                    "id": str(log.id),
                    "date": str(log.date),
                    "focus": log.parsed_record.get("focus") if log.parsed_record else None,
                    "duration_min": log.duration_min,
                    "rpe": log.rpe,
                    "raw_text": log.raw_text,
                }
                for log in logs
            ],
        },
        "uri": uri,
    }


async def _handle_reminders_status(params: dict, uri: str) -> dict:
    """fitness://reminders/status?user_id=xxx"""
    user_id = params.get("user_id", "").strip()
    if not user_id:
        return {"success": False, "error": "Missing required parameter: user_id", "uri": uri}

    from app.models.reminder_event import ReminderEvent
    from app.models.reminder import ReminderJob
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        # Active reminder jobs count
        result = await db.execute(
            select(ReminderJob).where(
                ReminderJob.user_id == user_id,
                ReminderJob.status == "active",
            )
        )
        active_jobs = len(result.scalars().all())

        # Recent reminder events
        result = await db.execute(
            select(ReminderEvent)
            .where(ReminderEvent.user_id == user_id)
            .order_by(ReminderEvent.triggered_at.desc())
            .limit(10)
        )
        events = result.scalars().all()

    return {
        "success": True,
        "data": {
            "active_jobs": active_jobs,
            "scheduler_running": is_scheduler_running(),
            "registered_jobs_total": get_registered_job_count(),
            "recent_events": [
                {
                    "id": str(e.id),
                    "message": e.message,
                    "status": e.status,
                    "triggered_at": str(e.triggered_at),
                }
                for e in events
            ],
        },
        "uri": uri,
    }
