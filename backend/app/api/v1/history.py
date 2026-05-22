from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.workout import LogWorkoutRequest, LogWorkoutResponse, WorkoutLogItem, MonthlySummary
from app.core.tools.log_workout import log_workout_record
from app.services.workout_service import get_workout_logs, get_monthly_summary, get_workout_log_by_id
from app.services.user_service import get_user_by_id

router = APIRouter(prefix="/history", tags=["History"])


@router.post("/log/{user_id}", response_model=LogWorkoutResponse)
async def log_workout(user_id: str, req: LogWorkoutRequest, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await log_workout_record(
        db=db,
        user_id=user_id,
        raw_text=req.raw_text,
        workout_date=req.date,
    )
    return LogWorkoutResponse(**result)


@router.get("/logs/{user_id}", response_model=list[WorkoutLogItem])
async def get_logs(
    user_id: str,
    year: int | None = Query(None),
    month: int | None = Query(None),
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
):
    logs = await get_workout_logs(db, user_id, year=year, month=month, limit=limit)
    return [WorkoutLogItem.model_validate(log) for log in logs]


@router.get("/log/{log_id}", response_model=WorkoutLogItem)
async def get_log(log_id: str, db: AsyncSession = Depends(get_db)):
    log = await get_workout_log_by_id(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Workout log not found")
    return WorkoutLogItem.model_validate(log)


@router.get("/monthly-summary/{user_id}", response_model=MonthlySummary)
async def monthly_summary(
    user_id: str,
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
):
    from app.services.plan_service import get_active_plan

    summary = await get_monthly_summary(db, user_id, year, month)

    # Calculate planned days from active plan
    plan = await get_active_plan(db, user_id)
    if plan and plan.plan_data:
        weekly_schedule = plan.plan_data.get("weekly_schedule", [])
        planned_days = len(weekly_schedule)
        # Rough estimate: planned_days * weeks in month
        import calendar
        _, days_in_month = calendar.monthrange(year, month)
        weeks_in_month = days_in_month / 7
        planned_days = round(planned_days * weeks_in_month)
    else:
        planned_days = summary["completed_days"]  # fallback

    completion_rate = summary["completed_days"] / planned_days if planned_days > 0 else 0.0

    return MonthlySummary(
        year=year,
        month=month,
        planned_days=planned_days,
        completed_days=summary["completed_days"],
        completion_rate=round(completion_rate, 2),
        streak_days=summary["streak_days"],
        total_duration_min=summary["total_duration_min"],
        by_focus=summary["by_focus"],
        daily_logs=summary["daily_logs"],
    )
