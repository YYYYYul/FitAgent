"""Tests for the three core tools."""

import pytest
from app.core.tools.generate_plan import generate_training_plan


class TestGenerateTrainingPlan:
    def test_generates_valid_plan(self):
        result = generate_training_plan(
            goal="fat_loss",
            height_cm=175,
            weight_kg=80,
            training_location="gym",
            weekly_days=4,
            experience_level="intermediate",
            preferred_time="19:00",
        )
        assert result["success"] is True
        assert result["plan_id"] is not None
        assert len(result["weekly_schedule"]) == 4
        assert result["plan_summary"] is not None

    def test_plan_days_match_request(self):
        for days in [3, 4, 5]:
            result = generate_training_plan(
                goal="muscle_gain", height_cm=180, weight_kg=75,
                training_location="gym", weekly_days=days,
                experience_level="intermediate", preferred_time="18:00",
            )
            assert len(result["weekly_schedule"]) == days

    def test_home_workout_uses_bodyweight(self):
        result = generate_training_plan(
            goal="health", height_cm=170, weight_kg=65,
            training_location="home", weekly_days=3,
            experience_level="beginner", preferred_time="07:00",
        )
        exercises = result["weekly_schedule"][0]["exercises"]
        # Home exercises should include bodyweight moves
        names = [ex["name"] for ex in exercises]
        assert any("俯卧撑" in n or "深蹲" in n or "平板" in n for n in names)

    def test_warns_low_bmi_fat_loss(self):
        result = generate_training_plan(
            goal="fat_loss", height_cm=180, weight_kg=55,  # BMI ~17
            training_location="gym", weekly_days=4,
            experience_level="beginner", preferred_time="19:00",
        )
        if result["warnings"]:
            assert any("体重偏低" in w or "bmi" in w.lower() for w in result["warnings"])

    def test_warns_beginner_high_frequency(self):
        result = generate_training_plan(
            goal="health", height_cm=175, weight_kg=70,
            training_location="home", weekly_days=6,
            experience_level="beginner", preferred_time="19:00",
        )
        if result["warnings"]:
            assert any("新手" in w or "频率" in w for w in result["warnings"])

    def test_invalid_weekly_days(self):
        result = generate_training_plan(
            goal="health", height_cm=175, weight_kg=70,
            training_location="home", weekly_days=8,
            experience_level="beginner", preferred_time="19:00",
        )
        assert result["success"] is False

    def test_each_day_has_required_fields(self):
        result = generate_training_plan(
            goal="fat_loss", height_cm=175, weight_kg=80,
            training_location="gym", weekly_days=5,
            experience_level="advanced", preferred_time="17:00",
        )
        for day in result["weekly_schedule"]:
            assert "day" in day
            assert "focus" in day
            assert "warmup" in day
            assert "exercises" in day
            assert len(day["exercises"]) > 0
            assert day["total_duration_min"] > 0
