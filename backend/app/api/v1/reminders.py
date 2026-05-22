"""
Reminders API — query reminder events and scheduler status (Phase 2C Step 1).

Endpoints:
  GET /reminders/events?user_id=X    — recent reminder trigger events
  GET /reminders/status              — scheduler health check
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.reminder_event import ReminderEvent
from app.core.reminder.scheduler import is_scheduler_running, get_registered_job_count

router = APIRouter(prefix="/reminders", tags=["Reminders"])


@router.get("/events")
async def get_reminder_events(
    user_id: str = Query(..., description="User ID to query events for"),
    limit: int = Query(20, ge=1, le=100, description="Max events to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Return recent reminder trigger events for a user.

    Events are ordered by triggered_at descending (most recent first).
    """
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
