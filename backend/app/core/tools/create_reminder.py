"""
Tool: create_weekly_reminder — persists reminder jobs to DB and registers
them with the APScheduler for real-time triggering (Phase 2C Step 1).

Input Schema:
    db: AsyncSession        — database session
    user_id: str            — target user
    plan_id: str            — associated training plan
    training_days: list     — [{day_of_week: int, remind_time: "HH:MM"}, ...]
    channel: str            — "web" (future: "email", "wechat")

Output Schema:
    {
        "success": bool,
        "reminder_jobs": [...],
        "summary": str,
        "scheduler_status": str   # Phase 2C: "registered" | "failed" | "unavailable"
    }

Internal Steps:
    1. Deactivate old reminder jobs for this plan
    2. Create new ReminderJob rows in DB
    3. Register each job with APScheduler (best-effort)
    4. Return summary + scheduler status
"""

import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from app.models.reminder import ReminderJob
from app.core.reminder.scheduler import register_reminder_job, is_scheduler_running


async def create_weekly_reminder(
    db: AsyncSession,
    user_id: str,
    plan_id: str,
    training_days: list[dict],
    channel: str = "web",
) -> dict:
    """
    Create weekly recurring reminder jobs and register with APScheduler.

    Scheduler registration is best-effort: if the scheduler is not running,
    the DB records are still created and the plan is not affected.
    """
    # Step 1: Deactivate old reminders for this plan
    await db.execute(
        update(ReminderJob)
        .where(ReminderJob.plan_id == plan_id, ReminderJob.status == "active")
        .values(status="deleted")
    )

    # Step 2: Create new ReminderJob rows in DB
    reminder_jobs = []
    scheduler_ok = is_scheduler_running()
    registered_count = 0

    for td in training_days:
        remind_time = td["remind_time"]
        job = ReminderJob(
            id=str(uuid.uuid4()),
            user_id=user_id,
            plan_id=plan_id,
            day_of_week=td["day_of_week"],
            remind_time=remind_time,
            channel=channel,
            status="active",
        )
        db.add(job)
        reminder_jobs.append({
            "job_id": str(job.id),
            "day_of_week": td["day_of_week"],
            "remind_time": td["remind_time"],
            "channel": channel,
            "next_trigger": (
                f"Next {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][td['day_of_week']]} at {td['remind_time']}"
            ),
        })

        # Step 3: Register with APScheduler (best-effort)
        if scheduler_ok:
            if register_reminder_job(str(job.id), td["day_of_week"], remind_time):
                registered_count += 1

    # Step 4: Build summary and scheduler status
    day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    days_str = "/".join(day_names[td["day_of_week"]] for td in training_days)

    if not scheduler_ok:
        scheduler_status = "unavailable"
    elif registered_count == len(training_days):
        scheduler_status = "registered"
    elif registered_count > 0:
        scheduler_status = f"partial ({registered_count}/{len(training_days)})"
    else:
        scheduler_status = "failed"

    return {
        "success": True,
        "reminder_jobs": reminder_jobs,
        "summary": f"已创建 {len(reminder_jobs)} 条每周提醒，每{days_str} {training_days[0]['remind_time'] if training_days else ''} 触发",
        "scheduler_status": scheduler_status,
    }
