from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.plan import GeneratePlanRequest, GeneratePlanResponse, PlanSummary
from app.core.tools.generate_plan import generate_training_plan
from app.services.plan_service import create_plan, get_active_plan, get_plan_history
from app.services.user_service import get_user_by_id

router = APIRouter(prefix="/plan", tags=["Plan"])


@router.post("/generate", response_model=GeneratePlanResponse)
async def generate_plan(req: GeneratePlanRequest, db: AsyncSession = Depends(get_db)):
    result = generate_training_plan(
        goal=req.goal,
        height_cm=req.height_cm,
        weight_kg=req.weight_kg,
        training_location=req.training_location,
        weekly_days=req.weekly_days,
        experience_level=req.experience_level,
        preferred_time=req.preferred_time,
    )
    return GeneratePlanResponse(**result)


@router.post("/save/{user_id}", response_model=PlanSummary)
async def save_plan(user_id: str, req: GeneratePlanRequest, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = generate_training_plan(
        goal=req.goal,
        height_cm=req.height_cm,
        weight_kg=req.weight_kg,
        training_location=req.training_location,
        weekly_days=req.weekly_days,
        experience_level=req.experience_level,
        preferred_time=req.preferred_time,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Plan generation failed"))

    plan = await create_plan(
        db=db,
        user_id=user_id,
        goal=req.goal,
        weekly_days=req.weekly_days,
        plan_data={"weekly_schedule": result["weekly_schedule"]},
        plan_summary=result["plan_summary"],
    )

    return PlanSummary(
        id=str(plan.id),
        status=plan.status,
        goal=plan.goal,
        weekly_days=plan.weekly_days,
        plan_summary=plan.plan_summary,
        plan_data=plan.plan_data,
        created_at=str(plan.created_at),
    )


@router.get("/active/{user_id}", response_model=PlanSummary | None)
async def get_active(user_id: str, db: AsyncSession = Depends(get_db)):
    plan = await get_active_plan(db, user_id)
    if not plan:
        return None
    return PlanSummary(
        id=str(plan.id),
        status=plan.status,
        goal=plan.goal,
        weekly_days=plan.weekly_days,
        plan_summary=plan.plan_summary,
        plan_data=plan.plan_data,
        created_at=str(plan.created_at),
    )


@router.get("/history/{user_id}", response_model=list[PlanSummary])
async def get_history(user_id: str, db: AsyncSession = Depends(get_db)):
    plans = await get_plan_history(db, user_id)
    return [
        PlanSummary(
            id=str(p.id),
            status=p.status,
            goal=p.goal,
            weekly_days=p.weekly_days,
            plan_summary=p.plan_summary,
            plan_data=p.plan_data,
            created_at=str(p.created_at),
        )
        for p in plans
    ]
