"""
Node: log_workout — parses natural language workout descriptions via LLM and saves to DB.

In:  state.user_input, state.user_id
Out: state.final_response, state.tools_called (log_workout_record result)
"""

from datetime import date
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.agent.state import AgentState
from app.core.agent.llm_client import LLMClient
from app.core.tools.log_workout import log_workout_record


async def log_workout_node(state: AgentState, db: AsyncSession, llm_client: Optional[LLMClient] = None) -> dict:
    """
    Parse user's natural language workout description via LLM, save to DB,
    and return a formatted summary response.
    """
    user_input = state.get("user_input", "")
    user_id = state.get("user_id", "")

    result = await log_workout_record(
        db=db,
        user_id=user_id,
        raw_text=user_input,
        workout_date=str(date.today()),
        llm=llm_client,
    )

    if result["success"]:
        parsed = result.get("parsed_record", {})
        exercises = parsed.get("exercises", [])
        focus = parsed.get("focus", "训练")
        duration = parsed.get("duration_min", "?")
        rpe = parsed.get("rpe", None)

        exercise_lines = "\n".join(
            f"  • {ex.get('name', '?')}: {ex.get('sets', '?')}组×{ex.get('reps', '?')}次"
            + (f" {ex.get('weight_kg', '')}kg" if ex.get('weight_kg') else "")
            for ex in exercises
        ) if exercises else "  (未能解析具体动作，已保存原始记录)"

        rpe_str = f"\n强度自评 RPE: {rpe}/10" if rpe else ""

        response = (
            f"已记录今天的训练！\n"
            f"部位：{focus}\n"
            f"时长：约{duration}分钟\n"
            f"动作：\n{exercise_lines}"
            f"{rpe_str}\n\n"
            f"记录已保存，继续保持！💪"
        )

        plan_consistency = result.get("plan_consistency")
        if plan_consistency and plan_consistency.get("matched_plan_day"):
            response += f"\n📋 匹配到训练计划：{plan_consistency['matched_plan_day']}（完成度 {int(plan_consistency.get('completion_rate', 0) * 100)}%）"
    else:
        response = f"抱歉，记录训练时出了点问题：{result.get('error', '未知错误')}。请再试一次。"

    return {
        "final_response": response,
        "intent": "log_workout",
        "tools_called": [{"tool": "log_workout_record", "result": result}],
        "requires_confirmation": False,
    }
