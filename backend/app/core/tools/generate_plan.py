"""
Tool 1: generate_training_plan
Generates a structured weekly training plan based on user profile and goals.
Uses template-based generation (MVP), with LLM enhancement planned for Phase 2.
"""

import uuid
from typing import Literal

# Exercise library
HOME_EXERCISES = {
    "胸": [
        {"name": "标准俯卧撑", "sets": 4, "reps": "12-15", "rest_sec": 60, "notes": "手比肩宽，核心收紧"},
        {"name": "窄距俯卧撑", "sets": 3, "reps": "10-12", "rest_sec": 60, "notes": "手窄距，刺激三头"},
        {"name": "上斜俯卧撑", "sets": 3, "reps": "12-15", "rest_sec": 60, "notes": "手放高台，刺激下胸"},
    ],
    "背": [
        {"name": "弹力带划船", "sets": 4, "reps": "12-15", "rest_sec": 60, "notes": "保持背部挺直"},
        {"name": "超人式", "sets": 3, "reps": "15", "rest_sec": 45, "notes": "俯卧，同时抬起手臂和腿"},
        {"name": "门框引体", "sets": 3, "reps": "8-12", "rest_sec": 90, "notes": "如有引体杆更佳"},
    ],
    "腿": [
        {"name": "自重深蹲", "sets": 4, "reps": "15-20", "rest_sec": 60, "notes": "膝盖不过脚尖，保持平衡"},
        {"name": "弓步蹲", "sets": 3, "reps": "12/每侧", "rest_sec": 60, "notes": "后腿膝盖轻触地面"},
        {"name": "臀桥", "sets": 3, "reps": "15-20", "rest_sec": 45, "notes": "臀部收紧，顶峰停留2秒"},
        {"name": "保加利亚分腿蹲", "sets": 3, "reps": "10/每侧", "rest_sec": 60, "notes": "后脚放椅子或沙发上"},
    ],
    "肩": [
        {"name": "俯身飞鸟(水瓶)", "sets": 3, "reps": "15", "rest_sec": 45, "notes": "用装满水的瓶子替代哑铃"},
        {"name": "侧平举(水瓶)", "sets": 3, "reps": "12-15", "rest_sec": 45, "notes": "肘部微弯，不要耸肩"},
    ],
    "核心": [
        {"name": "平板支撑", "sets": 3, "reps": "30-60秒", "rest_sec": 45, "notes": "保持身体一条直线"},
        {"name": "卷腹", "sets": 3, "reps": "15-20", "rest_sec": 45, "notes": "下巴不要贴胸口"},
        {"name": "俄罗斯转体", "sets": 3, "reps": "20/侧", "rest_sec": 45, "notes": "双脚抬离地面"},
    ],
}

GYM_EXERCISES = {
    "胸": [
        {"name": "杠铃卧推", "sets": 4, "reps": "8-12", "rest_sec": 90, "notes": "保持肩胛骨收紧"},
        {"name": "哑铃上斜卧推", "sets": 3, "reps": "10-12", "rest_sec": 75, "notes": "刺激上胸"},
        {"name": "龙门架夹胸", "sets": 3, "reps": "12-15", "rest_sec": 60, "notes": "顶峰收缩1秒"},
    ],
    "背": [
        {"name": "引体向上", "sets": 4, "reps": "8-12", "rest_sec": 90, "notes": "正手宽握，下巴过杠"},
        {"name": "杠铃划船", "sets": 4, "reps": "8-12", "rest_sec": 90, "notes": "背部挺直，杠铃沿大腿滑动"},
        {"name": "坐姿绳索划船", "sets": 3, "reps": "12-15", "rest_sec": 60, "notes": "肩胛骨带动手臂"},
    ],
    "腿": [
        {"name": "杠铃深蹲", "sets": 4, "reps": "8-12", "rest_sec": 120, "notes": "核心收紧，膝盖与脚尖同方向"},
        {"name": "罗马尼亚硬拉", "sets": 3, "reps": "10-12", "rest_sec": 90, "notes": "腘绳肌发力，保持腰背挺直"},
        {"name": "哑铃弓步走", "sets": 3, "reps": "12/每侧", "rest_sec": 60, "notes": "上身挺直，步幅适中"},
        {"name": "腿弯举", "sets": 3, "reps": "12-15", "rest_sec": 60, "notes": "控制离心收缩"},
    ],
    "肩": [
        {"name": "哑铃坐姿推举", "sets": 4, "reps": "8-12", "rest_sec": 75, "notes": "核心收紧，不要弓腰"},
        {"name": "哑铃侧平举", "sets": 3, "reps": "12-15", "rest_sec": 45, "notes": "肘部微弯，不要借力"},
        {"name": "面拉", "sets": 3, "reps": "15", "rest_sec": 45, "notes": "改善肩部健康，绳索拉向面部"},
    ],
    "手臂": [
        {"name": "杠铃弯举", "sets": 3, "reps": "10-12", "rest_sec": 60, "notes": "上臂固定，只动前臂"},
        {"name": "绳索下压", "sets": 3, "reps": "12-15", "rest_sec": 45, "notes": "大臂贴身体，充分伸展三头"},
    ],
    "核心": [
        {"name": "悬垂举腿", "sets": 3, "reps": "10-15", "rest_sec": 60, "notes": "控制摆动，用腹肌发力"},
        {"name": "绳索卷腹", "sets": 3, "reps": "15", "rest_sec": 45, "notes": "用腹部发力而不是手臂"},
    ],
}

# Split templates by goal and days per week
SPLIT_TEMPLATES = {
    3: {  # 3 days/week
        "fat_loss": [
            {"day": "Monday", "focus": "全身力量 + 有氧", "muscles": ["腿", "胸", "背", "核心"], "cardio": "30分钟中强度有氧"},
            {"day": "Wednesday", "focus": "全身力量 + 有氧", "muscles": ["腿", "肩", "背", "核心"], "cardio": "30分钟中强度有氧"},
            {"day": "Friday", "focus": "全身力量 + 有氧", "muscles": ["腿", "胸", "手臂", "核心"], "cardio": "30分钟中强度有氧"},
        ],
        "muscle_gain": [
            {"day": "Monday", "focus": "全身（下肢重点）", "muscles": ["腿", "肩", "核心"]},
            {"day": "Wednesday", "focus": "全身（上肢重点）", "muscles": ["胸", "背", "手臂"]},
            {"day": "Friday", "focus": "全身（强度提升）", "muscles": ["腿", "胸", "背", "核心"]},
        ],
        "health": [
            {"day": "Monday", "focus": "全身轻度训练", "muscles": ["腿", "胸", "核心"]},
            {"day": "Wednesday", "focus": "全身轻度训练", "muscles": ["背", "肩", "核心"]},
            {"day": "Friday", "focus": "全身轻度训练", "muscles": ["腿", "胸", "背", "核心"]},
        ],
    },
    4: {  # 4 days/week - Upper/Lower split
        "fat_loss": [
            {"day": "Monday", "focus": "上肢 + 有氧", "muscles": ["胸", "背", "肩", "核心"], "cardio": "25分钟中强度有氧"},
            {"day": "Tuesday", "focus": "下肢 + 有氧", "muscles": ["腿", "核心"], "cardio": "25分钟中强度有氧"},
            {"day": "Thursday", "focus": "上肢 + 有氧", "muscles": ["胸", "背", "手臂", "核心"], "cardio": "25分钟中强度有氧"},
            {"day": "Saturday", "focus": "下肢 + 有氧", "muscles": ["腿", "核心"], "cardio": "25分钟中强度有氧"},
        ],
        "muscle_gain": [
            {"day": "Monday", "focus": "上肢推 + 核心", "muscles": ["胸", "肩", "手臂", "核心"]},
            {"day": "Tuesday", "focus": "下肢（腿部重点）", "muscles": ["腿", "核心"]},
            {"day": "Thursday", "focus": "上肢拉 + 核心", "muscles": ["背", "手臂", "核心"]},
            {"day": "Saturday", "focus": "下肢（综合强化）", "muscles": ["腿", "核心"]},
        ],
        "health": [
            {"day": "Monday", "focus": "上肢轻度", "muscles": ["胸", "背", "肩"]},
            {"day": "Wednesday", "focus": "下肢轻度", "muscles": ["腿", "核心"]},
            {"day": "Friday", "focus": "上肢轻度", "muscles": ["胸", "背", "手臂", "核心"]},
            {"day": "Sunday", "focus": "全身轻度", "muscles": ["腿", "肩", "核心"]},
        ],
    },
    5: {  # 5 days/week - PPLUL (Push/Pull/Legs/Upper/Lower)
        "fat_loss": [
            {"day": "Monday", "focus": "推类动作 + 有氧", "muscles": ["胸", "肩", "手臂"], "cardio": "20分钟HIIT"},
            {"day": "Tuesday", "focus": "拉类动作 + 有氧", "muscles": ["背", "手臂"], "cardio": "20分钟中等有氧"},
            {"day": "Wednesday", "focus": "腿部 + 有氧", "muscles": ["腿", "核心"], "cardio": "20分钟HIIT"},
            {"day": "Friday", "focus": "上肢综合 + 有氧", "muscles": ["胸", "背", "肩", "手臂"], "cardio": "20分钟中等有氧"},
            {"day": "Saturday", "focus": "下肢综合 + 有氧", "muscles": ["腿", "核心"], "cardio": "20分钟HIIT"},
        ],
        "muscle_gain": [
            {"day": "Monday", "focus": "胸 + 三头", "muscles": ["胸", "手臂"]},
            {"day": "Tuesday", "focus": "背 + 二头", "muscles": ["背", "手臂"]},
            {"day": "Wednesday", "focus": "腿 + 肩", "muscles": ["腿", "肩"]},
            {"day": "Friday", "focus": "上肢综合", "muscles": ["胸", "背", "肩", "手臂"]},
            {"day": "Saturday", "focus": "下肢综合", "muscles": ["腿", "核心"]},
        ],
        "health": [
            {"day": "Monday", "focus": "推类轻度", "muscles": ["胸", "肩"]},
            {"day": "Tuesday", "focus": "拉类轻度", "muscles": ["背", "手臂"]},
            {"day": "Wednesday", "focus": "腿部轻度", "muscles": ["腿", "核心"]},
            {"day": "Friday", "focus": "上肢轻度", "muscles": ["胸", "背", "肩"]},
            {"day": "Saturday", "focus": "全身轻松练", "muscles": ["腿", "核心", "手臂"]},
        ],
    },
}

WARMUP_TEMPLATES = {
    "beginner": "5分钟动态拉伸 + 5分钟跳绳或原地踏步",
    "intermediate": "10分钟有氧(跑步/跳绳) + 动态拉伸",
    "advanced": "10分钟有氧 + 动态拉伸 + 目标动作热身组(轻重量)",
}

COOLDOWN_TEMPLATES = {
    "beginner": "5分钟静态拉伸",
    "intermediate": "5-10分钟静态拉伸 + 泡沫轴放松",
    "advanced": "10分钟静态拉伸 + 泡沫轴放松",
}


def _pick_exercises(muscles: list[str], location: str, experience: str) -> list[dict]:
    """Pick 3-5 exercises for the given muscle groups."""
    lib = GYM_EXERCISES if location == "gym" else HOME_EXERCISES
    selected = []
    for muscle in muscles:
        if muscle in lib:
            # Pick exercises based on experience
            exercises = lib[muscle]
            if experience == "beginner":
                exercises = exercises[:2]  # 2 exercises per muscle for beginners
            elif experience == "advanced":
                exercises = exercises  # All exercises for advanced
            else:
                exercises = exercises[:3]  # Up to 3 for intermediate

            for ex in exercises:
                selected.append(ex)
    return selected[:6]  # Cap at 6 exercises per day


def generate_training_plan(
    goal: Literal["fat_loss", "muscle_gain", "health"],
    height_cm: float,
    weight_kg: float,
    training_location: Literal["home", "gym"],
    weekly_days: int,
    experience_level: Literal["beginner", "intermediate", "advanced"],
    preferred_time: str = "19:00",
) -> dict:
    """
    Generate a structured weekly training plan.

    Returns the plan as a dict matching the GeneratePlanResponse schema.
    """
    # Validate weekly_days
    if weekly_days < 1 or weekly_days > 7:
        return {"success": False, "error": "weekly_days must be between 1 and 7"}

    # Normalize: use 3-day split for 1-2 days, 5-day split for 6-7 days
    if weekly_days <= 2:
        template_key = 3
    elif weekly_days >= 6:
        template_key = 5
    else:
        template_key = weekly_days

    # Get template for goal and days
    templates = SPLIT_TEMPLATES.get(template_key, {})
    if goal not in templates:
        goal = "health"  # fallback
    schedule_template = templates[goal]

    # Build weekly schedule
    weekly_schedule = []
    warnings = []
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    # If weekly_days is less than the template, take the first N
    schedule = schedule_template[:weekly_days]

    for entry in schedule:
        exercises = _pick_exercises(entry["muscles"], training_location, experience_level)
        cardio = entry.get("cardio", None)

        day_plan = {
            "day": entry["day"],
            "focus": entry["focus"],
            "warmup": WARMUP_TEMPLATES.get(experience_level, WARMUP_TEMPLATES["beginner"]),
            "exercises": exercises,
            "cardio": cardio,
            "cooldown": COOLDOWN_TEMPLATES.get(experience_level, COOLDOWN_TEMPLATES["beginner"]),
            "total_duration_min": sum(ex["sets"] * ex["rest_sec"] for ex in exercises) // 60 + 20 + (25 if cardio else 10),
        }
        weekly_schedule.append(day_plan)

    # Generate warnings
    bmi = weight_kg / ((height_cm / 100) ** 2)
    if bmi < 18.5 and goal == "fat_loss":
        warnings.append("你的体重偏低(BMI<18.5)，不建议以减脂为主要目标。建议优先增重并加强营养摄入。")
    elif bmi > 30 and goal == "muscle_gain":
        warnings.append("你的体重偏高(BMI>30)，建议先以减脂为目标，配合力量训练保留肌肉。")
    if weekly_days >= 6 and experience_level == "beginner":
        warnings.append("作为新手，每周6-7天训练频率偏高，建议降低到3-5天以保证充分恢复。")
    if training_location == "home" and goal == "muscle_gain":
        warnings.append("在家训练增肌效果有限。建议至少准备弹力带和可调节哑铃以增加负重。")

    goal_labels = {"fat_loss": "减脂", "muscle_gain": "增肌", "health": "健康维持"}
    location_labels = {"home": "在家训练", "gym": "健身房"}
    experience_labels = {"beginner": "新手", "intermediate": "中级", "advanced": "高级"}

    plan_summary = (
        f"这是一个为期一周的{goal_labels.get(goal, '')}计划，"
        f"每周训练{weekly_days}天，"
        f"训练地点为{location_labels.get(training_location, '')}，"
        f"适合{experience_labels.get(experience_level, '')}水平。"
        f"每日训练预计{weekly_schedule[0]['total_duration_min'] if weekly_schedule else 60}分钟左右。"
    )

    return {
        "success": True,
        "plan_id": str(uuid.uuid4()),
        "weekly_schedule": weekly_schedule,
        "plan_summary": plan_summary,
        "warnings": warnings if warnings else None,
    }
