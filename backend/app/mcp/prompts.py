"""
MCP Prompt registry for FitAgent (Phase 3B Step 4).

Prompts are workflow templates that guide an MCP Client (e.g., Claude Desktop)
through multi-step tasks. Each prompt specifies:
  - Which Resources to read (state inspection)
  - Which Tools to call (actions)
  - Recommended workflow sequence
  - Expected output format

WHY Prompts matter:
  Prompts are the "orchestration layer" of MCP. They tell the calling Agent
  HOW to combine FitAgent's tools and resources to accomplish a goal.
  This demonstrates Agent engineering capability beyond simple tool calling.

Prompt categories:
  - Planning:    create-fitness-plan
  - Review:      weekly-review, monthly-summary-analysis
  - Analysis:    workout-consistency-check
  - Guidance:    beginner-guidance

All prompts output structured markdown for consistent display in MCP Clients.
"""

# =========================================================================
# Prompt definitions
# =========================================================================

PROMPT_DEFINITIONS = {
    "create-fitness-plan": {
        "name": "create-fitness-plan",
        "description": (
            "Guide for creating a complete personalized fitness training plan. "
            "Covers: checking existing plans, generating a new plan, and setting up reminders."
        ),
        "category": "planning",
        "version": "1.0",
        "arguments": [
            {"name": "goal", "description": "Training goal: fat_loss, muscle_gain, or health", "required": True},
            {"name": "weekly_days", "description": "Number of training days per week (1-7)", "required": True},
            {"name": "training_location", "description": "home or gym", "required": True},
            {"name": "experience_level", "description": "beginner, intermediate, or advanced", "required": True},
        ],
        "workflow": {
            "steps": [
                {
                    "step": 1,
                    "action": "read_resource",
                    "resource": "fitness://active-plan?user_id={user_id}",
                    "purpose": "Check if user already has an active training plan.",
                },
                {
                    "step": 2,
                    "action": "conditional",
                    "condition": "If an active plan exists",
                    "guidance": "Ask the user whether they want to replace it. If yes, proceed. If no, stop.",
                },
                {
                    "step": 3,
                    "action": "call_tool",
                    "tool": "generate_training_plan",
                    "arguments": {
                        "goal": "{goal}",
                        "height_cm": "{height_cm}",
                        "weight_kg": "{weight_kg}",
                        "training_location": "{training_location}",
                        "weekly_days": "{weekly_days}",
                        "experience_level": "{experience_level}",
                        "preferred_time": "{preferred_time}",
                    },
                    "purpose": "Generate a structured weekly training plan.",
                },
                {
                    "step": 4,
                    "action": "call_tool",
                    "tool": "create_weekly_reminder",
                    "arguments": {
                        "user_id": "{user_id}",
                        "plan_id": "{plan_id}",
                        "training_days": "{training_days}",
                    },
                    "purpose": "Create weekly recurring reminders for the new plan.",
                },
            ],
        },
        "output_format": "markdown",
        "output_template": (
            "# 训练计划\n\n"
            "## 计划概要\n{plan_summary}\n\n"
            "## 每周安排\n{weekly_schedule}\n\n"
            "## 注意事项\n{warnings}\n\n"
            "## 提醒状态\n{reminder_status}\n\n"
            "> 完成后记得用 log_workout_record 记录每次训练。"
        ),
    },

    "weekly-review": {
        "name": "weekly-review",
        "description": (
            "Weekly training review workflow. Analyzes recent workouts, compares with the plan, "
            "and provides actionable feedback on consistency and progress."
        ),
        "category": "review",
        "version": "1.0",
        "arguments": [
            {"name": "user_id", "description": "User ID to review", "required": True},
        ],
        "workflow": {
            "steps": [
                {
                    "step": 1,
                    "action": "read_resource",
                    "resource": "fitness://history/latest?user_id={user_id}&limit=7",
                    "purpose": "Get the last 7 days of workout records.",
                },
                {
                    "step": 2,
                    "action": "read_resource",
                    "resource": "fitness://active-plan?user_id={user_id}",
                    "purpose": "Get the current training plan for comparison.",
                },
                {
                    "step": 3,
                    "action": "analysis",
                    "guidance": (
                        "Compare planned vs actual workouts:\n"
                        "- How many planned days were completed?\n"
                        "- Which focus areas were covered? Which were missed?\n"
                        "- Average RPE and duration trends\n"
                        "- Consistency score (completed / planned)"
                    ),
                },
            ],
        },
        "output_format": "markdown",
        "output_template": (
            "# 周度训练复盘\n\n"
            "## 完成情况\n- 计划训练: {planned} 天\n- 实际完成: {completed} 天\n- 完成率: {completion_rate}%\n\n"
            "## 部位覆盖\n{by_focus}\n\n"
            "## 训练强度\n- 平均 RPE: {avg_rpe}\n- 总时长: {total_duration} 分钟\n\n"
            "## 建议\n{suggestions}\n\n"
            "> 连续训练天数: {streak_days} 天"
        ),
    },

    "monthly-summary-analysis": {
        "name": "monthly-summary-analysis",
        "description": (
            "Monthly training data analysis. Generates a comprehensive report on training "
            "volume, consistency, focus distribution, and trends."
        ),
        "category": "review",
        "version": "1.0",
        "arguments": [
            {"name": "user_id", "description": "User ID", "required": True},
            {"name": "year", "description": "Year (e.g., 2026)", "required": False},
            {"name": "month", "description": "Month (1-12)", "required": False},
        ],
        "workflow": {
            "steps": [
                {
                    "step": 1,
                    "action": "read_resource",
                    "resource": "fitness://monthly-summary?user_id={user_id}&year={year}&month={month}",
                    "purpose": "Get monthly training statistics.",
                },
                {
                    "step": 2,
                    "action": "read_resource",
                    "resource": "fitness://active-plan?user_id={user_id}",
                    "purpose": "Get plan info for completion rate calculation.",
                },
                {
                    "step": 3,
                    "action": "analysis",
                    "guidance": (
                        "Analyze the monthly data:\n"
                        "- Completion rate vs previous months (trend)\n"
                        "- Most/least trained focus areas\n"
                        "- Total volume (duration) and whether it meets goals\n"
                        "- Streak continuity\n"
                        "- Key improvement areas for next month"
                    ),
                },
            ],
        },
        "output_format": "markdown",
        "output_template": (
            "# {year}年{month}月 月度训练报告\n\n"
            "## 核心指标\n"
            "| 指标 | 数值 |\n|------|------|\n"
            "| 训练天数 | {completed}/{planned} |\n"
            "| 完成率 | {completion_rate}% |\n"
            "| 总时长 | {total_duration} 分钟 |\n"
            "| 连续天数 | {streak_days} 天 |\n\n"
            "## 部位分布\n{by_focus}\n\n"
            "## 月度总结\n{analysis}\n\n"
            "## 下月建议\n{recommendations}"
        ),
    },

    "workout-consistency-check": {
        "name": "workout-consistency-check",
        "description": (
            "Compare recent workout logs with the training plan to check consistency. "
            "Identifies missed focus areas, overtraining risks, and schedule adherence."
        ),
        "category": "analysis",
        "version": "1.0",
        "arguments": [
            {"name": "user_id", "description": "User ID", "required": True},
        ],
        "workflow": {
            "steps": [
                {
                    "step": 1,
                    "action": "read_resource",
                    "resource": "fitness://history/latest?user_id={user_id}&limit=14",
                    "purpose": "Get recent 14 days of workouts.",
                },
                {
                    "step": 2,
                    "action": "read_resource",
                    "resource": "fitness://active-plan?user_id={user_id}",
                    "purpose": "Get the active training plan for comparison.",
                },
                {
                    "step": 3,
                    "action": "analysis",
                    "guidance": (
                        "Consistency analysis:\n"
                        "- Compare each day's actual workout focus vs planned focus\n"
                        "- Flag days where workout was skipped\n"
                        "- Check if any muscle group is over-trained (>2x in 3 days)\n"
                        "- Calculate schedule adherence rate\n"
                        "- Highlight if user is self-modifying the plan"
                    ),
                },
            ],
        },
        "output_format": "markdown",
        "output_template": (
            "# 训练一致性分析\n\n"
            "## 计划执行\n- 计划执行率: {adherence_rate}%\n- 跳过天数: {missed_days}\n"
            "- 额外训练: {extra_workouts} 天\n\n"
            "## 部位覆盖\n{coverage_table}\n\n"
            "## 风险提示\n{risk_warnings}\n\n"
            "## 建议\n- 保持: {strengths}\n- 改进: {improvements}"
        ),
    },

    "beginner-guidance": {
        "name": "beginner-guidance",
        "description": (
            "Beginner-friendly fitness guidance. Searches the knowledge base for "
            "beginner principles and provides a structured starting checklist."
        ),
        "category": "guidance",
        "version": "1.0",
        "arguments": [
            {"name": "topic", "description": "Specific topic (e.g., '第一次去健身房', '新手训练频率')", "required": False},
        ],
        "workflow": {
            "steps": [
                {
                    "step": 1,
                    "action": "call_tool",
                    "tool": "search_fitness_knowledge",
                    "arguments": {"query": "新手训练原则 {topic}", "top_k": 5},
                    "purpose": "Search knowledge base for beginner-relevant content.",
                },
                {
                    "step": 2,
                    "action": "analysis",
                    "guidance": (
                        "Organize knowledge base results into:\n"
                        "- Core principles (2-3 key takeaways)\n"
                        "- Practical first steps (what to do this week)\n"
                        "- Common mistakes to avoid\n"
                        "- Recommended next actions (e.g., create a plan)"
                    ),
                },
            ],
        },
        "output_format": "markdown",
        "output_template": (
            "# 新手健身指南: {topic}\n\n"
            "## 核心原则\n{principles}\n\n"
            "## 本周行动清单\n- [ ] {action_1}\n- [ ] {action_2}\n- [ ] {action_3}\n\n"
            "## 常见误区\n{mistakes}\n\n"
            "## 下一步\n{next_steps}\n\n"
            "> 参考来源: {sources}"
        ),
    },
}


# =========================================================================
# Public API
# =========================================================================


def list_prompts() -> list[dict]:
    """
    Return all registered prompt definitions (MCP prompts/list response).

    Each prompt includes name, description, category, version, and arguments.
    The full workflow is returned only in prompts/get to keep the list compact.
    """
    return [
        {
            "name": p["name"],
            "description": p["description"],
            "category": p["category"],
            "version": p["version"],
            "arguments": p["arguments"],
        }
        for p in PROMPT_DEFINITIONS.values()
    ]


def get_prompt(name: str, arguments: dict | None = None) -> dict:
    """
    Get a full prompt definition with rendered workflow.

    Args:
        name: prompt name (e.g., "create-fitness-plan")
        arguments: optional dict of argument values for template rendering

    Returns:
        On success: {"success": true, "prompt": {...full definition with messages...}}
        On unknown: {"success": false, "error": "..."}
    """
    prompt = PROMPT_DEFINITIONS.get(name)
    if prompt is None:
        return {
            "success": False,
            "error": f"Unknown prompt: {name}. Available: {list(PROMPT_DEFINITIONS.keys())}",
        }

    # Build the prompt messages that an MCP Client would use
    messages = _build_prompt_messages(prompt, arguments or {})

    return {
        "success": True,
        "prompt": {
            "name": prompt["name"],
            "description": prompt["description"],
            "category": prompt["category"],
            "version": prompt["version"],
            "arguments": prompt["arguments"],
            "workflow": prompt["workflow"],
            "output_format": prompt["output_format"],
            "messages": messages,
        },
    }


def _build_prompt_messages(prompt: dict, arguments: dict) -> list[dict]:
    """
    Build the MCP prompt messages (system + user) that guide the MCP Client.

    The system message describes the role and workflow.
    The user message provides the specific task with rendered context.
    """
    # Fill in argument placeholders
    args_str = ", ".join(
        f"{a['name']}={arguments.get(a['name'], '?')}" for a in prompt["arguments"]
    ) if prompt["arguments"] else ""

    # Build workflow description
    workflow_steps = prompt["workflow"]["steps"]
    steps_text = ""
    for s in workflow_steps:
        action = s["action"]
        if action == "read_resource":
            steps_text += f"\n{s['step']}. 读取数据: {s['resource']}"
            steps_text += f"\n   目的: {s['purpose']}"
        elif action == "call_tool":
            steps_text += f"\n{s['step']}. 调用工具: {s['tool']}"
            steps_text += f"\n   参数: {s.get('arguments', {})}"
            steps_text += f"\n   目的: {s['purpose']}"
        elif action == "conditional":
            steps_text += f"\n{s['step']}. [条件判断] {s.get('condition', '')}"
            steps_text += f"\n   {s.get('guidance', '')}"
        elif action == "analysis":
            steps_text += f"\n{s['step']}. 分析: {s.get('guidance', '')}"

    return [
        {
            "role": "system",
            "content": {
                "type": "text",
                "text": (
                    f"You are a FitAgent fitness advisor executing the '{prompt['name']}' workflow.\n"
                    f"Category: {prompt['category']}\n"
                    f"Version: {prompt['version']}\n\n"
                    f"## Workflow{steps_text}\n\n"
                    f"## Output Format\n{prompt['output_format']}\n\n"
                    f"## Rules\n"
                    f"- Follow the workflow steps in order\n"
                    f"- Use the specified resources and tools by name\n"
                    f"- Output in the specified markdown format\n"
                    f"- Never give medical diagnoses or drug recommendations\n"
                    f"- If data is missing, note it in the output rather than halting"
                ),
            },
        },
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": (
                    f"Execute the '{prompt['name']}' workflow.\n"
                    f"Arguments: {args_str}\n\n"
                    f"Expected output: {prompt['output_format']} markdown.\n"
                    f"Output template: {prompt.get('output_template', '')}"
                ),
            },
        },
    ]
