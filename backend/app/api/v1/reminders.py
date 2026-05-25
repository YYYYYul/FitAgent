"""
Reminders API — query reminder events, scheduler status, and upcoming reminders.

Endpoints:
  GET /reminders/events?user_id=X     — recent reminder trigger events
  GET /reminders/status               — scheduler health check
  GET /reminders/next?user_id=X       — next upcoming reminder for this user
"""

from datetime import datetime, date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.reminder_event import ReminderEvent
from app.models.reminder import ReminderJob
from app.core.reminder.scheduler import is_scheduler_running, get_registered_job_count

router = APIRouter(prefix="/reminders", tags=["Reminders"])


@router.get("/events")
async def get_reminder_events(
    user_id: str = Query(..., description="User ID to query events for"),
    limit: int = Query(20, ge=1, le=100, description="Max events to return"),
    db: AsyncSession = Depends(get_db),
):
    """Return recent reminder trigger events, newest first."""
    result = await db.execute(
        select(ReminderEvent)
        .where(ReminderEvent.user_id == user_id)
        .order_by(ReminderEvent.triggered_at.desc())
        .limit(limit)
    )
    events = result.scalars().all()

    return {
        "user_id": user_id,
        "count": len(events),
        "events": [
            {
                "id": str(e.id),
                "reminder_job_id": str(e.reminder_job_id),
                "plan_id": str(e.plan_id) if e.plan_id else None,
                "message": e.message,
                "status": e.status,
                "triggered_at": str(e.triggered_at),
            }
            for e in events
        ],
    }


@router.get("/status")
async def get_reminder_status():
    """Return current scheduler health status."""
    return {
        "scheduler_running": is_scheduler_running(),
        "registered_jobs": get_registered_job_count(),
    }


@router.get("/next")
async def get_next_reminder(
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the next upcoming reminder for a user.

    Calculates which active reminder job will fire next based on current day/time.
    """
    result = await db.execute(
        select(ReminderJob).where(
            ReminderJob.user_id == user_id,
            ReminderJob.status == "active",
        )
    )
    jobs = result.scalars().all()

    if not jobs:
        return {"has_next": False, "message": "No active reminders"}

    # Find the next upcoming reminder
    now = datetime.now()
    today_dow = now.weekday()  # 0=Monday
    current_time = now.strftime("%H:%M")

    candidates = []
    day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    for job in jobs:
        days_until = (job.day_of_week - today_dow) % 7
        # If same day but time already passed, push to next week
        if days_until == 0 and job.remind_time <= current_time:
            days_until = 7
        next_date = now.date() + timedelta(days=days_until)
        candidates.append({
            "job_id": str(job.id),
            "plan_id": str(job.plan_id),
            "day_of_week": job.day_of_week,
            "day_label": day_names[job.day_of_week],
            "remind_time": job.remind_time,
            "next_date": str(next_date),
            "days_until": days_until,
        })

    if not candidates:
        return {"has_next": False, "message": "No upcoming reminders"}

    # Return the closest one
    candidates.sort(key=lambda c: c["days_until"])
    nearest = candidates[0]

    return {
        "has_next": True,
        "next_reminder": nearest,
        "all_upcoming": candidates[:7],  # next 7 days
        "total_active": len(jobs),
        "scheduler_running": is_scheduler_running(),
    }
