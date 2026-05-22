"""
Guardrails: input validation and safety checks for the agent.
"""

import re

# Sensitive/off-topic patterns to reject
BLOCKED_PATTERNS = [
    r"(医疗|诊断|治病|处方|药物|手术|疾病)",
    r"(自杀|自残|伤害|暴力|违法)",
    r"(政治|宗教)",
]

# Max input length
MAX_INPUT_LENGTH = 2000


def validate_input(user_input: str) -> tuple[bool, str | None]:
    """
    Validate user input before processing.

    Returns:
        (is_valid, error_message)
    """
    if not user_input or not user_input.strip():
        return False, "输入不能为空，请输入你的问题或需求。"

    if len(user_input) > MAX_INPUT_LENGTH:
        return False, f"输入过长，请控制在{MAX_INPUT_LENGTH}字符以内。"

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, user_input):
            return False, "抱歉，这个问题超出了我的能力范围。我是健身助手，只能回答与健身训练相关的问题。"

    return True, None


def sanitize_response(response: str) -> str:
    """Sanitize agent response before sending to user."""
    # Remove any system instructions that might leak
    response = re.sub(r'<\|system\|>.*?<\|/system\|>', '', response, flags=re.DOTALL)
    return response.strip()
