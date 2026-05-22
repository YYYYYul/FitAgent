"""
MCP Adapter: create_weekly_reminder — wraps core/tools/create_reminder.py.

Takes MCP arguments (user_id, plan_id, training_days, channel), calls
create_weekly_reminder() via a database session, returns structured result.
The underlying tool handles APScheduler registration automatically.
"""

from app.db.session import AsyncSessionLocal
from app.core.tools.create_reminder import create_weekly_reminder


async def handle_create_weekly_reminder(arguments: dict) -> dict:
    """
    Handle MCP 'create_weekly_reminder' tool call.

    Args:
        arguments: {
            user_id: str,
            plan_id: str,
            training_days: [{day_of_week: int (0=Mon), remind_time: "HH:MM"}, ...],
            channel?: str (default "web")
        }

    Returns:
        {success, reminder_jobs, summary, scheduler_status, error, source}
    """
    # Step 1: Validate required fields
    for field in ["user_id", "plan_id", "training_days"]:
        if field not in arguments:
            return {
                "success": False,
                "error": f"Missing required argument: {field}.",
                "source": "mcp",
            }

    user_id = str(arguments["user_id"])
    plan_id = str(arguments["plan_id"])
    training_days = arguments["training_days"]
    channel = str(arguments.get("channel", "web"))

    # Step 2: Validate training_days structure
    if not isinstance(training_days, list) or len(training_days) == 0:
        return {
            "success": False,
            "error": "training_days must be a non-empty list of {day_of_week: int, remind_time: str}.",
            "source": "mcp",
        }

    for td in training_days:
        if not isinstance(td, dict):
            return {"success": False, "error": "Each training_days entry must be a dict.", "source": "mcp"}
        if "day_of_week" not in td or "remind_time" not in td:
            return {"success": False, "error": "Each entry needs day_of_week (int 0-6) and remind_time (HH:MM).", "source": "mcp"}
        dow = td["day_of_week"]
        if not isinstance(dow, int) or dow < 0 or dow > 6:
            return {"success": False, "error": f"day_of_week must be 0-6, got {dow}.", "source": "mcp"}
        rt = td["remind_time"]
        if not isinstance(rt, str) or ":" not in rt:
            return {"success": False, "error": f"remind_time must be HH:MM, got {rt}.", "source": "mcp"}
        try:
            hour, minute = map(int, str(rt).split(":"))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                return {"success": False, "error": f"remind_time must be valid HH:MM (00:00-23:59), got {rt}.", "source": "mcp"}
        except ValueError:
            return {"success": False, "error": f"remind_time must be HH:MM, got {rt}.", "source": "mcp"}

    # Step 3: Call existing tool
    try:
        async with AsyncSessionLocal() as db:
            result = await create_weekly_reminder(
                db=db,
                user_id=user_id,
                plan_id=plan_id,
                training_days=training_days,
                channel=channel,
            )
    except Exception as e:
        return {
            "success": False,
            "error": f"Reminder creation failed: {str(e)}",
            "source": "mcp",
        }

    result["source"] = "mcp"
    return result
