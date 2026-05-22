"""
MCP Tool registry for FitAgent (Phase 3B Step 2 — full tool set).

Registered tools:
  1. generate_training_plan    — generate a weekly training plan
  2. log_workout_record        — parse and save a workout log
  3. search_fitness_knowledge  — RAG retrieval from fitness knowledge base
  4. create_weekly_reminder    — create weekly training reminders
"""

from app.mcp.adapters.plan_adapter import handle_generate_training_plan
from app.mcp.adapters.workout_adapter import handle_log_workout_record
from app.mcp.adapters.rag_adapter import handle_search_fitness_knowledge
from app.mcp.adapters.reminder_adapter import handle_create_weekly_reminder

# Tool handler registry: name → async handler function
TOOL_HANDLERS = {
    "generate_training_plan": handle_generate_training_plan,
    "log_workout_record": handle_log_workout_record,
    "search_fitness_knowledge": handle_search_fitness_knowledge,
    "create_weekly_reminder": handle_create_weekly_reminder,
}

# Tool definitions (for MCP tools/list response)
TOOL_DEFINITIONS = [
    {
        "name": "generate_training_plan",
        "description": (
            "Generate a structured weekly fitness training plan based on user profile and goals. "
            "Supports fat_loss, muscle_gain, and health goals for both home and gym training. "
            "Returns a complete weekly schedule with exercises, sets, reps, rest times, warmup, and cardio."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User ID (UUID). Optional."},
                "goal": {"type": "string", "enum": ["fat_loss", "muscle_gain", "health"], "description": "Training goal."},
                "height_cm": {"type": "number", "description": "Height in cm (1-300)."},
                "weight_kg": {"type": "number", "description": "Weight in kg (1-500)."},
                "training_location": {"type": "string", "enum": ["home", "gym"], "description": "Training location."},
                "weekly_days": {"type": "integer", "minimum": 1, "maximum": 7, "description": "Days per week."},
                "experience_level": {"type": "string", "enum": ["beginner", "intermediate", "advanced"], "description": "Experience level."},
                "preferred_time": {"type": "string", "description": "Preferred time HH:MM (default 19:00)."},
            },
            "required": ["goal", "height_cm", "weight_kg", "training_location", "weekly_days", "experience_level"],
        },
    },
    {
        "name": "log_workout_record",
        "description": (
            "Parse a natural language workout description and save it as a structured workout log. "
            "Supports Chinese descriptions with exercise names, sets, reps, and weights. "
            "Automatically matches against the user's training plan to calculate completion rate."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User ID (UUID). Optional."},
                "raw_text": {"type": "string", "description": "Natural language workout description (e.g., '今天练了胸，卧推60kg 5x5')."},
                "date": {"type": "string", "description": "Workout date YYYY-MM-DD. Defaults to today."},
            },
            "required": ["raw_text"],
        },
    },
    {
        "name": "search_fitness_knowledge",
        "description": (
            "Search the FitAgent fitness knowledge base (RAG) for relevant information. "
            "Returns top-K matching knowledge chunks with relevance scores. "
            "Covers: beginner principles, fat loss, muscle gain, PPL training, home/gym exercises, "
            "training frequency, rest & recovery, and common mistakes. "
            "This tool only retrieves knowledge — it does NOT generate a final answer."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Fitness question to search for (e.g., '新手一周练几次')."},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 10, "description": "Max results (default 3)."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "create_weekly_reminder",
        "description": (
            "Create weekly recurring reminder jobs for a training plan. "
            "Each reminder is registered with the APScheduler for automatic triggering. "
            "Deactivates any old reminders for the same plan before creating new ones."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User ID (UUID)."},
                "plan_id": {"type": "string", "description": "Training plan ID (UUID)."},
                "training_days": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "day_of_week": {"type": "integer", "minimum": 0, "maximum": 6, "description": "0=Monday ... 6=Sunday"},
                            "remind_time": {"type": "string", "description": "HH:MM format (e.g., '19:00')"},
                        },
                        "required": ["day_of_week", "remind_time"],
                    },
                    "description": "List of training day schedules.",
                },
                "channel": {"type": "string", "description": "Notification channel (default 'web')."},
            },
            "required": ["user_id", "plan_id", "training_days"],
        },
    },
]


def list_tools() -> list[dict]:
    """Return the list of registered tool definitions (MCP tools/list response)."""
    return TOOL_DEFINITIONS


async def call_tool(name: str, arguments: dict) -> dict:
    """
    Execute a tool by name with the given arguments.

    Returns:
        On success: {success: true, ...tool-specific fields, source: "mcp"}
        On unknown tool: {success: false, error: "Unknown tool: ...", source: "mcp"}
        On handler error: {success: false, error: "Tool execution failed: ...", source: "mcp"}
    """
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return {
            "success": False,
            "error": f"Unknown tool: {name}. Available: {list(TOOL_HANDLERS.keys())}",
            "source": "mcp",
        }
    try:
        return await handler(arguments)
    except Exception as e:
        return {
            "success": False,
            "error": f"Tool execution failed: {str(e)}",
            "source": "mcp",
        }
