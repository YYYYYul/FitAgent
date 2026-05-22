import uuid
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.sql import extract

from app.models.workout import WorkoutLog


async def create_workout_log(
    db: AsyncSession,
    user_id: str,
    raw_text: str,
    workout_date: date,
    parsed_record: dict | None = None,
    duration_min: int | None = None,
    rpe: int | None = None,
    plan_id: str | None = None,
) -> WorkoutLog:
    log = WorkoutLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        plan_id=plan_id,
        date=workout_date,
        raw_text=raw_text,
        parsed_record=parsed_record,
        duration_min=duration_min,
        rpe=rpe,
    )
    db.add(log)
    await db.flush()
    return log


async def get_workout_logs(
    db: AsyncSession,
    user_id: str,
    year: int | None = None,
    month: int | None = None,
    limit: int = 50,
) -> list[WorkoutLog]:
    query = select(WorkoutLog).where(WorkoutLog.user_id == user_id)
    if year and month:
        query = query.where(
            extract("year", WorkoutLog.date) == year,
            extract("month", WorkoutLog.date) == month,
        )
    query = query.order_by(WorkoutLog.date.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_workout_log_by_id(db: AsyncSession, log_id: str) -> WorkoutLog | None:
    result = await db.execute(select(WorkoutLog).where(WorkoutLog.id == log_id))
    return result.scalar_one_or_none()


async def get_monthly_summary(db: AsyncSession, user_id: str, year: int, month: int) -> dict:
    logs = await get_workout_logs(db, user_id, year=year, month=month)
    completed_days = len(set(log.date for log in logs))
    total_duration = sum(log.duration_min or 0 for log in logs)

    by_focus: dict[str, int] = {}
    for log in logs:
        if log.parsed_record and log.parsed_record.get("focus"):
            focus = log.parsed_record["focus"]
            by_focus[focus] = by_focus.get(focus, 0) + 1

    # Calculate streak
    streak = 0
    today = date.today()
    check_date = today
    dates_set = {log.date for log in logs}
    while check_date in dates_set:
        streak += 1
        check_date = check_date.replace(day=check_date.day - 1) if check_date.day > 1 else (
            check_date.replace(month=check_date.month - 1, day=28) if check_date.month > 1 else
            check_date.replace(year=check_date.year - 1, month=12, day=31)
        )

    return {
        "year": year,
        "month": month,
        "completed_days": completed_days,
        "completion_rate": 0.0,  # will be calculated by caller with plan info
        "streak_days": streak,
        "total_duration_min": total_duration,
        "by_focus": by_focus,
        "daily_logs": [
            {
                "date": str(log.date),
                "focus": log.parsed_record.get("focus") if log.parsed_record else None,
                "duration_min": log.duration_min,
                "rpe": log.rpe,
            }
            for log in logs
        ],
    }
