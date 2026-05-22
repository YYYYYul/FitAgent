"""
create_plan Node (MVP): generates and saves a training plan.
Full Plan-Execute-Replan subgraph comes in Phase 2.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.agent.state import AgentState
from app.core.tools.generate_plan import generate_training_plan
from app.services.plan_service import create_plan, get_active_plan
from app.services.user_service import get_user_by_id


async def create_plan_node(state: AgentState, db: AsyncSession, llm_client=None) -> dict:
    """Handle training plan creation."""
    user_id = state.get("user_id", "")
    user_input = state.get("user_input", "")
    user_profile = state.get("user_profile")

    # Check if user profile is complete
    if not user_profile:
        return {
            "final_response": (
                "要制定训练计划，我需要先了解你的身体信息。请告诉我：\n"
                "1. 身高（cm）\n"
                "2. 体重（kg）\n"
                "3. 训练目标（减脂/增肌/健康维持）\n"
                "4. 在哪训练（在家/健身房）\n"
                "5. 每周能练几天（1-7天）\n"
                "6. 训练经验（新手/中级/高级）\n\n"
                "例如：「我身高175、体重80、想减脂、在健身房、一周练4天、中级水平」"
            ),
            "intent": "create_plan",
            "requires_confirmation": False,
            "error": "user_profile_incomplete",
        }

    # Extract goal and other params from user input if they're re-specifying
    # MVP: use stored profile values
    goal = user_profile.get("goal", "health")
    height = user_profile.get("height_cm")
    weight = user_profile.get("weight_kg")
    location = user_profile.get("training_location", "home")
    weekly_days = user_profile.get("weekly_days", 3)
    experience = user_profile.get("experience_level", "beginner")
    preferred_time = user_profile.get("preferred_time", "19:00")

    if not height or not weight:
        return {
            "final_response": "请先完善你的身高和体重信息，我才能生成专属的训练计划。你可以在个人资料中填写。",
            "intent": "create_plan",
            "requires_confirmation": False,
            "error": "missing_body_info",
        }

    # Generate plan
    result = generate_training_plan(
        goal=goal,
        height_cm=float(height),
        weight_kg=float(weight),
        training_location=location,
        weekly_days=int(weekly_days),
        experience_level=experience,
        preferred_time=str(preferred_time),
    )

    if not result["success"]:
        return {
            "final_response": f"生成计划失败：{result.get('error', '未知错误')}",
            "intent": "create_plan",
            "requires_confirmation": False,
        }

    # Save plan to DB
    plan = await create_plan(
        db=db,
        user_id=user_id,
        goal=goal,
        weekly_days=int(weekly_days),
        plan_data={"weekly_schedule": result["weekly_schedule"]},
        plan_summary=result["plan_summary"],
    )

    # Format response
    response = f"📋 已为你生成训练计划！\n\n{result['plan_summary']}\n\n"

    for day in result["weekly_schedule"]:
        response += f"【{day['day']}】{day['focus']}\n"
        response += f"  热身：{day['warmup']}\n"
        for ex in day["exercises"]:
            response += f"  • {ex['name']} {ex['sets']}组×{ex['reps']}次 (休息{ex['rest_sec']}秒)\n"
        if day.get("cardio"):
            response += f"  有氧：{day['cardio']}\n"
        response += f"  拉伸：{day.get('cooldown', '5分钟静态拉伸')}\n"
        response += f"  预计时长：{day['total_duration_min']}分钟\n\n"

    if result.get("warnings"):
        response += "⚠️ 注意事项：\n"
        for w in result["warnings"]:
            response += f"  • {w}\n"

    response += "\n这个计划需要调整吗？你可以说「把周三的训练换到周四」或「增加有氧时间」。"
    response += "\n\n另外，需要我为此计划创建每周训练提醒吗？"

    return {
        "final_response": response,
        "intent": "create_plan",
        "tools_called": [
            {"tool": "generate_training_plan", "result": {"plan_id": str(plan.id), "success": True}},
            {"tool": "create_plan", "result": {"plan_id": str(plan.id)}},
        ],
        "requires_confirmation": False,
    }
