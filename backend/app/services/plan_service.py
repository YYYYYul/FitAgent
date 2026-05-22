import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.plan import TrainingPlan


async def create_plan(db: AsyncSession, user_id: str, goal: str, weekly_days: int, plan_data: dict, plan_summary: str) -> TrainingPlan:
    # Deactivate existing active plan
    await db.execute(
        update(TrainingPlan)
        .where(TrainingPlan.user_id == user_id, TrainingPlan.status == "active")
        .values(status="archived")
    )
    plan = TrainingPlan(
        id=str(uuid.uuid4()),
        user_id=user_id,
        status="active",
        goal=goal,
        weekly_days=weekly_days,
        plan_data=plan_data,
        plan_summary=plan_summary,
        version=1,
    )
    db.add(plan)
    await db.flush()
    return plan


async def get_active_plan(db: AsyncSession, user_id: str) -> TrainingPlan | None:
    result = await db.execute(
        select(TrainingPlan).where(
            TrainingPlan.user_id == user_id,
            TrainingPlan.status == "active",
        )
    )
    return result.scalar_one_or_none()


async def get_plan_by_id(db: AsyncSession, plan_id: str) -> TrainingPlan | None:
    result = await db.execute(select(TrainingPlan).where(TrainingPlan.id == plan_id))
    return result.scalar_one_or_none()


async def get_plan_history(db: AsyncSession, user_id: str) -> list[TrainingPlan]:
    result = await db.execute(
        select(TrainingPlan)
        .where(TrainingPlan.user_id == user_id)
        .order_by(TrainingPlan.created_at.desc())
        .limit(20)
    )
    return list(result.scalars().all())


async def update_plan(
    db: AsyncSession,
    plan_id: str,
    plan_data: dict | None = None,
    plan_summary: str | None = None,
    goal: str | None = None,
    weekly_days: int | None = None,
) -> TrainingPlan | None:
    plan = await get_plan_by_id(db, plan_id)
    if not plan:
        return None
    if plan_data is not None:
        plan.plan_data = plan_data
    if plan_summary is not None:
        plan.plan_summary = plan_summary
    if goal is not None:
        plan.goal = goal
    if weekly_days is not None:
        plan.weekly_days = weekly_days
    plan.version += 1
    await db.flush()
    return plan
