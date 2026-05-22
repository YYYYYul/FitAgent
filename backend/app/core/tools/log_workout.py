"""
Tool: log_workout_record — parses natural language workout descriptions into
structured records using LLM, then saves to the database.

Input Schema:
    db: AsyncSession        — database session
    user_id: str            — target user
    raw_text: str           — natural language workout description
    workout_date: str|None  — "YYYY-MM-DD", defaults to today
    llm: LLMClient|None     — LLM client for parsing; None → no parsing

Output Schema:
    {
        "success": bool,
        "log_id": str | None,
        "parsed_record": {...} | None,
        "plan_consistency": {"matched_plan_day": str, "completion_rate": float} | None,
        "error": str | None
    }

Internal Steps:
    1. Parse workout_date → Python date object
    2. If LLM is available: call chat_structured() with WORKOUT_PARSE_PROMPT
    3. If LLM unavailable / error: store raw_text only as minimal record
    4. Match against active training plan to calculate completion rate
    5. Write to workout_log table → return structured result
"""

import json
from datetime import date
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.workout_service import create_workout_log
from app.services.plan_service import get_active_plan
from app.core.agent.llm_client import LLMClient

WORKOUT_PARSE_PROMPT = """You are a workout data parser. Extract structured workout data from the user's natural language input.

Output ONLY valid JSON with this exact structure:
{
    "focus": "训练部位 (e.g., 胸+三头, 背+二头, 腿, 全身)",
    "duration_min": estimated total minutes (integer),
    "exercises": [
        {
            "name": "exercise name in Chinese",
            "sets": number of sets (integer),
            "reps": number of reps (integer, use average if range given),
            "weight_kg": weight in kg (float, null if bodyweight),
            "rpe": RPE 1-10 (integer, null if not mentioned)
        }
    ],
    "rpe": overall session RPE 1-10 (integer, null if not mentioned),
    "notes": "any additional notes from the user"
}

If a field cannot be determined, use null. Exercise names should be in Chinese.

User input: {raw_text}

JSON output:"""


async def log_workout_record(
    db: AsyncSession,
    user_id: str,
    raw_text: str,
    workout_date: Optional[str] = None,
    llm: Optional[LLMClient] = None,
) -> dict:
    """
    Parse natural language workout log and save to database.

    When LLM is available:  uses chat_structured() for accurate parsing with JSON schema.
    When LLM is unavailable:  stores raw text only, skipping structured extraction.
    """
    # Step 1: Parse date
    if workout_date:
        try:
            workout_date_obj = date.fromisoformat(workout_date)
        except ValueError:
            return {"success": False, "error": f"Invalid date format: {workout_date}. Use YYYY-MM-DD."}
    else:
        workout_date_obj = date.today()

    # Step 2: LLM-based parsing (when available)
    parsed_record = None
    if llm and llm.is_available:
        try:
            prompt = WORKOUT_PARSE_PROMPT.format(raw_text=raw_text)
            parsed_record = await llm.chat_structured(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500,
            )
        except Exception:
            # LLM parsing failed → fallback: store raw text only
            parsed_record = {"raw": raw_text, "focus": "解析失败", "exercises": []}
    else:
        # No LLM available → minimal record
        parsed_record = {"raw": raw_text, "focus": "未解析", "exercises": []}

    # Step 3: Match against active training plan (plan consistency check)
    plan_consistency = None
    active_plan = None
    try:
        active_plan = await get_active_plan(db, user_id)
        if active_plan and active_plan.plan_data:
            plan_data = active_plan.plan_data
            weekday = workout_date_obj.weekday()  # 0=Monday
            day_names_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            day_name = day_names_en[weekday]

            weekly_schedule = plan_data.get("weekly_schedule", [])
            matched = None
            for day_plan in weekly_schedule:
                if day_plan.get("day") == day_name:
                    matched = day_plan
                    break

            if matched:
                planned_exercises = len(matched.get("exercises", []))
                actual_exercises = len(parsed_record.get("exercises", [])) if parsed_record else 0
                completion = min(actual_exercises / planned_exercises, 1.0) if planned_exercises > 0 else 0.0
                plan_consistency = {
                    "matched_plan_day": day_name,
                    "completion_rate": round(completion, 2),
                }
    except Exception:
        pass

    # Step 4: Extract metadata and save to DB
    duration_min = parsed_record.get("duration_min") if parsed_record else None
    rpe = parsed_record.get("rpe") if parsed_record else None

    log = await create_workout_log(
        db=db,
        user_id=user_id,
        raw_text=raw_text,
        workout_date=workout_date_obj,
        parsed_record=parsed_record,
        duration_min=duration_min,
        rpe=rpe,
        plan_id=str(active_plan.id) if active_plan else None,
    )

    # Step 5: Return structured result
    return {
        "success": True,
        "log_id": str(log.id),
        "parsed_record": {
            "date": str(workout_date_obj),
            "focus": parsed_record.get("focus") if parsed_record else None,
            "duration_min": duration_min,
            "exercises": parsed_record.get("exercises", []) if parsed_record else [],
            "rpe": rpe,
            "notes": parsed_record.get("notes") if parsed_record else None,
        },
        "plan_consistency": plan_consistency,
    }
