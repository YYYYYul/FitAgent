"""
APScheduler-based reminder scheduler (Phase 2C Step 1).

WHY APScheduler as MVP:
  Single-process, in-memory scheduler. No Celery, no Redis, no external infra.
  Sufficient for a single-instance demo. Phase 3 can upgrade to Celery + Redis
  for multi-worker deployments without changing the scheduler interface.

Job ID format:
  reminder:{reminder_job_id}
  This makes each job uniquely identifiable and easy to remove/update by ID.

Scheduler lifecycle:
  - Start:   FastAPI lifespan startup → init_scheduler()
  - Recover: query all active reminder_job rows → register cron jobs
  - Stop:    FastAPI lifespan shutdown → shutdown_scheduler()
  - Failure: scheduler init failure logs a warning; the system keeps running
             without scheduled reminders (DB records are preserved)

Callback flow when a job fires:
  reminder_callback(reminder_job_id)
    → query ReminderJob, UserProfile, TrainingPlan
    → generate reminder message text
    → create ReminderEvent(status="sent")
    → log to Agent Trace (via tools_called convention)
"""

import uuid
import logging
from datetime import datetime, time
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.reminder import ReminderJob
from app.models.reminder_event import ReminderEvent
from app.models.user import UserProfile
from app.models.plan import TrainingPlan

logger = logging.getLogger("fitagent.reminder")

# Module-level singleton
_scheduler: Optional[AsyncIOScheduler] = None
_registered_jobs: set[str] = set()  # tracks job IDs already registered


# =========================================================================
# Public API — called from FastAPI lifespan
# =========================================================================


def get_scheduler() -> Optional[AsyncIOScheduler]:
    """Return the singleton scheduler instance, or None if not initialized."""
    return _scheduler


def is_scheduler_running() -> bool:
    return _scheduler is not None and _scheduler.running


async def init_scheduler() -> bool:
    """
    Initialize the APScheduler and restore active jobs from DB.
    Called once at FastAPI startup.

    Returns True if scheduler started successfully, False if degraded.
    """
    global _scheduler

    try:
        _scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
        _scheduler.start()
        logger.info("[Reminder] APScheduler started")

        # Restore existing active jobs from DB
        await _restore_jobs_from_db()
        logger.info(f"[Reminder] Restored {len(_registered_jobs)} active jobs from DB")
        return True

    except Exception as e:
        logger.warning(f"[Reminder] Scheduler initialization failed: {e}. System will run without scheduled reminders.")
        _scheduler = None
        return False


async def shutdown_scheduler() -> None:
    """Gracefully shut down the APScheduler. Called at FastAPI shutdown."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        _registered_jobs.clear()
        logger.info("[Reminder] Scheduler shut down")


# =========================================================================
# Job registration — called by create_weekly_reminder tool
# =========================================================================


def register_reminder_job(reminder_job_id: str, day_of_week: int, remind_time_str: str) -> bool:
    """
    Register a single reminder as a weekly cron job in APScheduler.

    Args:
        reminder_job_id: UUID of the ReminderJob row
        day_of_week: 0=Monday ... 6=Sunday
        remind_time_str: "HH:MM" format

    Returns:
        True if registered successfully, False if scheduler unavailable or error
    """
    if not is_scheduler_running():
        logger.warning(f"[Reminder] Cannot register job {reminder_job_id}: scheduler not running")
        return False

    job_id = f"reminder:{reminder_job_id}"
    if job_id in _registered_jobs:
        return True  # already registered

    try:
        if not remind_time_str or ":" not in str(remind_time_str):
            logger.warning(f"[Reminder] Invalid remind_time for job {reminder_job_id}: {remind_time_str}")
            return False
        hour, minute = map(int, str(remind_time_str).split(":"))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return False
        trigger = CronTrigger(
            day_of_week=day_of_week,
            hour=hour,
            minute=minute,
            timezone="Asia/Shanghai",
        )
        _scheduler.add_job(
            reminder_callback,
            trigger=trigger,
            id=job_id,
            args=[reminder_job_id],
            replace_existing=True,
        )
        _registered_jobs.add(job_id)
        logger.info(f"[Reminder] Registered job {job_id}: day={day_of_week} time={remind_time_str}")
        return True

    except Exception as e:
        logger.error(f"[Reminder] Failed to register job {reminder_job_id}: {e}")
        return False


def unregister_reminder_job(reminder_job_id: str) -> bool:
    """
    Remove a reminder job from APScheduler (when plan is updated/deleted).

    Returns True if removed, False if not found or scheduler unavailable.
    """
    if not is_scheduler_running():
        return False

    job_id = f"reminder:{reminder_job_id}"
    try:
        if job_id in _registered_jobs:
            _scheduler.remove_job(job_id)
            _registered_jobs.discard(job_id)
            return True
    except Exception as e:
        logger.error(f"[Reminder] Failed to unregister job {reminder_job_id}: {e}")
    return False


def get_registered_job_count() -> int:
    return len(_registered_jobs)


# =========================================================================
# Callback — invoked when a cron job fires
# =========================================================================


async def reminder_callback(reminder_job_id: str) -> None:
    """
    Callback invoked by APScheduler when a reminder cron job triggers.

    Flow:
      1. Open a DB session
      2. Query ReminderJob, UserProfile, TrainingPlan
      3. Generate reminder message text
      4. Create ReminderEvent(status="sent")
      5. Close session

    If any step fails, creates a ReminderEvent(status="failed") for visibility.
    """
    async with AsyncSessionLocal() as db:
        try:
            # Step 1: Query reminder job
            result = await db.execute(select(ReminderJob).where(ReminderJob.id == reminder_job_id))
            job = result.scalar_one_or_none()
            if not job or job.status != "active":
                return  # job was deactivated or deleted

            # Step 2: Query user and plan
            user_result = await db.execute(select(UserProfile).where(UserProfile.id == job.user_id))
            user = user_result.scalar_one_or_none()

            plan_result = await db.execute(select(TrainingPlan).where(TrainingPlan.id == job.plan_id))
            plan = plan_result.scalar_one_or_none()

            # Step 3: Generate message
            message = _build_reminder_message(user, plan, job)

            # Step 4: Create event
            event = ReminderEvent(
                id=str(uuid.uuid4()),
                user_id=job.user_id,
                reminder_job_id=reminder_job_id,
                plan_id=job.plan_id,
                message=message,
                status="sent",
                triggered_at=datetime.now(),
                created_at=datetime.now(),
            )
            db.add(event)
            await db.commit()
            logger.info(f"[Reminder] Fired: job={reminder_job_id} user={job.user_id}")

        except Exception as e:
            await db.rollback()
            logger.error(f"[Reminder] Callback failed for job {reminder_job_id}: {e}")
            # Try to record the failure
            try:
                event = ReminderEvent(
                    id=str(uuid.uuid4()),
                    user_id="unknown",
                    reminder_job_id=reminder_job_id,
                    message=f"Reminder callback failed: {e}",
                    status="failed",
                    triggered_at=datetime.now(),
                    created_at=datetime.now(),
                )
                db.add(event)
                await db.commit()
            except Exception:
                pass


# =========================================================================
# Internal helpers
# =========================================================================


async def _restore_jobs_from_db() -> None:
    """
    On scheduler startup, query all active ReminderJob rows and register them.
    This ensures reminders survive server restarts.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ReminderJob).where(ReminderJob.status == "active")
        )
        jobs = result.scalars().all()

        for job in jobs:
            # Validate job data before attempting registration (skip corrupted rows)
            if job.remind_time is None or job.remind_time == "None" or ":" not in str(job.remind_time):
                logger.warning(f"[Reminder] Skipping job {job.id}: invalid remind_time={job.remind_time}")
                continue
            if job.day_of_week is None or not (0 <= int(job.day_of_week) <= 6):
                logger.warning(f"[Reminder] Skipping job {job.id}: invalid day_of_week={job.day_of_week}")
                continue

            register_reminder_job(
                reminder_job_id=str(job.id),
                day_of_week=int(job.day_of_week),
                remind_time_str=str(job.remind_time),
            )


def _build_reminder_message(
    user: Optional[UserProfile],
    plan: Optional[TrainingPlan],
    job: ReminderJob,
) -> str:
    """
    Generate a human-readable reminder message from the training plan.

    Tries to find the matching day's training focus from the plan.
    Falls back to a generic message if plan data is unavailable.
    """
    day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    day_label = day_names[job.day_of_week] if 0 <= job.day_of_week < 7 else "训练日"

    # Try to find matching day in plan
    focus = ""
    duration = ""
    if plan and plan.plan_data:
        weekly_schedule = plan.plan_data.get("weekly_schedule", [])
        day_names_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        target_day = day_names_en[job.day_of_week] if 0 <= job.day_of_week < 7 else ""
        for day_plan in weekly_schedule:
            if day_plan.get("day") == target_day:
                focus = day_plan.get("focus", "")
                duration = f"{day_plan.get('total_duration_min', '?')} 分钟"
                break

    if focus:
        return f"🏋️ {day_label}训练提醒\n\n今天训练：{focus}\n预计时长：{duration}\n\n完成后记得来记录训练哦！💪"
    else:
        return f"🏋️ {day_label}训练提醒\n\n今天是你的训练日，记得完成训练计划！\n完成后记得来记录训练哦！💪"
