"""
MCP Adapter: generate_training_plan — thin wrapper around core/tools/generate_plan.py.

WHY adapter instead of re-implementation:
  The adapter only translates MCP tool arguments → generate_training_plan() parameters
  and formats the result for MCP. All business logic stays in the existing tool layer.
  This is a pure integration layer — zero business logic lives here.

Flow:
  MCP arguments → validate → call generate_training_plan() → wrap MCP response
"""

from app.core.tools.generate_plan import generate_training_plan
from app.config import get_settings


async def handle_generate_training_plan(arguments: dict) -> dict:
    """
    Handle the MCP 'generate_training_plan' tool call.

    Args:
        arguments: MCP tool arguments (see tools.py for inputSchema)

    Returns:
        {
            "success": bool,
            "plan_id": str | None,
            "weekly_schedule": [...] | None,
            "plan_summary": str | None,
            "warnings": [...] | None,
            "error": str | None,
            "source": "mcp"
        }
    """
    # Step 1: Extract and validate required arguments
    required_fields = ["goal", "height_cm", "weight_kg", "training_location", "weekly_days", "experience_level"]
    missing = [f for f in required_fields if f not in arguments]
    if missing:
        return {
            "success": False,
            "error": f"Missing required arguments: {', '.join(missing)}. "
                     f"Provide: goal, height_cm, weight_kg, training_location, weekly_days, experience_level.",
            "source": "mcp",
        }

    # Step 2: Validate argument values
    try:
        goal = str(arguments["goal"])
        height_cm = float(arguments["height_cm"])
        weight_kg = float(arguments["weight_kg"])
        training_location = str(arguments["training_location"])
        weekly_days = int(arguments["weekly_days"])
        experience_level = str(arguments["experience_level"])
        preferred_time = str(arguments.get("preferred_time", "19:00"))
    except (ValueError, TypeError) as e:
        return {
            "success": False,
            "error": f"Invalid argument type: {e}",
            "source": "mcp",
        }

    # Step 3: Validate enum values
    if goal not in ("fat_loss", "muscle_gain", "health"):
        return {"success": False, "error": f"Invalid goal: {goal}. Must be fat_loss, muscle_gain, or health.", "source": "mcp"}

    if training_location not in ("home", "gym"):
        return {"success": False, "error": f"Invalid training_location: {training_location}. Must be home or gym.", "source": "mcp"}

    if experience_level not in ("beginner", "intermediate", "advanced"):
        return {"success": False, "error": f"Invalid experience_level: {experience_level}.", "source": "mcp"}

    if weekly_days < 1 or weekly_days > 7:
        return {"success": False, "error": f"weekly_days must be 1-7, got {weekly_days}.", "source": "mcp"}

    if height_cm <= 0 or height_cm > 300:
        return {"success": False, "error": f"height_cm must be 1-300, got {height_cm}.", "source": "mcp"}

    if weight_kg <= 0 or weight_kg > 500:
        return {"success": False, "error": f"weight_kg must be 1-500, got {weight_kg}.", "source": "mcp"}

    # Step 4: Call existing tool
    try:
        result = generate_training_plan(
            goal=goal,
            height_cm=height_cm,
            weight_kg=weight_kg,
            training_location=training_location,
            weekly_days=weekly_days,
            experience_level=experience_level,
            preferred_time=preferred_time,
        )
    except Exception as e:
        return {
            "success": False,
            "error": f"Plan generation failed: {str(e)}",
            "source": "mcp",
        }

    # Step 5: Add MCP metadata
    result["source"] = "mcp"
    return result
