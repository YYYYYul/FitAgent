"""
query_history Node: queries workout history, calendar, and monthly summaries.
"""

from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.agent.state import AgentState
from app.services.workout_service import get_workout_logs, get_monthly_summary
from app.services.plan_service import get_active_plan


async def query_history_node(state: AgentState, db: AsyncSession, llm_client=None) -> dict:
    """Handle workout history queries."""
    user_input = state.get("user_input", "")
    user_id = state.get("user_id", "")

    today = date.today()

    # Determine if asking about this month or specific month
    if "这个月" in user_input or "本月" in user_input or "月" in user_input:
        year, month = today.year, today.month
    else:
        year, month = today.year, today.month

    summary = await get_monthly_summary(db, user_id, year, month)

    # Get recent logs
    logs = await get_workout_logs(db, user_id, year=year, month=month, limit=10)

    plan = await get_active_plan(db, user_id)
    planned = 0
    if plan and plan.plan_data:
        import calendar
        _, days_in_month = calendar.monthrange(year, month)
        weekly_schedule = plan.plan_data.get("weekly_schedule", [])
        planned = round(len(weekly_schedule) * days_in_month / 7)

    completed = summary["completed_days"]
    completion_rate = completed / planned if planned > 0 else 0

    # Build response
    month_name = f"{year}年{month}月"
    response = f"📊 {month_name}训练复盘\n\n"
    response += f"训练完成：{completed}天 / 计划{planned}天\n"
    response += f"完成率：{completion_rate:.0%}\n"
    response += f"连续训练：{summary['streak_days']}天\n"
    response += f"总训练时长：{summary['total_duration_min']}分钟\n"

    if summary["by_focus"]:
        response += "\n部位分布：\n"
        for focus, count in sorted(summary["by_focus"].items(), key=lambda x: x[1], reverse=True):
            response += f"  • {focus}: {count}次\n"

    if logs:
        response += "\n最近训练：\n"
        for log in logs[:5]:
            rpe_str = f" RPE {log.rpe}/10" if log.rpe else ""
            focus = log.parsed_record.get("focus", "") if log.parsed_record else ""
            response += f"  • {log.date} {focus} ({log.duration_min or '?'}分钟{rpe_str})\n"

    if completion_rate >= 0.8:
        response += "\n表现优秀，继续保持！🌟"
    elif completion_rate >= 0.5:
        response += "\n还不错，再努力一点就能达成目标！💪"
    else:
        response += "\n这月训练偏少，下个月加油追回来！"

    return {
        "final_response": response,
        "intent": "query_history",
        "requires_confirmation": False,
    }
