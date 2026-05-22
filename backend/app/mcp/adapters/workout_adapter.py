"""
MCP Adapter: log_workout_record — wraps core/tools/log_workout.py.

Takes MCP arguments (raw_text, date, user_id), calls log_workout_record()
via a database session, and returns structured MCP content.
"""

from datetime import date
from app.db.session import AsyncSessionLocal
from app.core.tools.log_workout import log_workout_record


async def handle_log_workout_record(arguments: dict) -> dict:
    """
    Handle MCP 'log_workout_record' tool call.

    Args:
        arguments: {user_id?: str, raw_text: str, date?: str "YYYY-MM-DD"}

    Returns:
        {success, log_id, parsed_record, plan_consistency, error, source}
    """
    # Step 1: Validate required fields
    if "raw_text" not in arguments or not arguments["raw_text"].strip():
        return {
            "success": False,
            "error": "Missing required argument: raw_text (the workout description).",
            "source": "mcp",
        }
    if "user_id" not in arguments or not arguments["user_id"]:
        return {
            "success": False,
            "error": "Missing required argument: user_id (the user who did the workout).",
            "source": "mcp",
        }

    raw_text = arguments["raw_text"].strip()
    user_id = arguments["user_id"]
    workout_date = arguments.get("date")

    # Step 2: Validate date format if provided
    if workout_date:
        try:
            date.fromisoformat(workout_date)
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid date format: {workout_date}. Use YYYY-MM-DD.",
                "source": "mcp",
            }

    # Step 3: Call existing tool via DB session
    try:
        async with AsyncSessionLocal() as db:
            result = await log_workout_record(
                db=db,
                user_id=user_id,
                raw_text=raw_text,
                workout_date=workout_date,
                llm=None,  # MCP doesn't use LLM for parsing in this context
            )
    except Exception as e:
        return {
            "success": False,
            "error": f"Workout log failed: {str(e)}",
            "source": "mcp",
        }

    result["source"] = "mcp"
    return result
