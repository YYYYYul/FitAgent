"""
Intent Router — Layer 1 (LLM classification via LLMClient) + Layer 2 (keyword fallback).

Routing strategy:
1. LLM classification (primary):  uses LLMClient.chat_structured() when available
2. Keyword fallback (secondary):  activated when LLM is unavailable OR confidence < 0.7
3. Ultimate fallback:             casual_chat when all else fails

Key design decisions (WHY):
- Confidence threshold of 0.7:  below this the LLM is uncertain enough that keyword
  rules are more reliable and safer for routing to tool-invoking intents
- Fallback to casual_chat on unknown:  prevents the agent from taking wrong actions
  (e.g., calling generate_plan when the user is just chatting)
"""

import json
import re
from typing import Optional

from app.core.agent.llm_client import LLMClient

# ------------------------------------------------------------------
# Keyword patterns — curated for Chinese fitness input
# Each keyword list is designed to catch the most common phrasings
# while avoiding cross-intent false positives
# ------------------------------------------------------------------

INTENT_KEYWORDS = {
    "log_workout": ["练了", "刚练", "训练完", "完成了", "做了", "组", "kg", "公斤", "哑铃", "杠铃", "卧推", "深蹲", "硬拉"],
    "create_plan": ["制定", "生成", "计划", "帮我安排", "设计", "创建", "做个计划", "安排一下"],
    "update_plan": ["修改", "改", "调整", "换", "更新计划", "换成", "改一下计划"],
    "query_history": ["这周", "这个月", "历史", "日历", "完成率", "复盘", "总结", "查询", "练了几", "看看"],
    "fitness_qa": ["怎么练", "怎么做", "如何", "为什么", "是什么", "能不能", "可以吗", "正确", "错误", "建议", "推荐", "应该", "还是", "区别", "选择", "哪个好", "新手", "多久", "几次", "合适", "适合", "注意"],
}

# ------------------------------------------------------------------
# Intent classification prompt (used with LLM)
# ------------------------------------------------------------------

INTENT_PROMPT = """You are the FitAgent intent classifier. Classify the user's input into exactly ONE intent.

Intent types:
- casual_chat: casual conversation, greetings, off-topic chat, unrelated questions
- fitness_qa: fitness knowledge questions (how to, what is, why, can I, advice, recommendations)
- create_plan: user wants to create/generate a NEW training plan
- update_plan: user wants to modify/adjust an existing plan
- log_workout: user is recording workout details (exercises done, sets, reps, weights)
- query_history: user wants to view workout history, calendar, completion rate, review

Output ONLY valid JSON:
{"intent": "...", "confidence": 0.0-1.0, "reason": "one sentence reason"}

Examples:
"今天练了胸，卧推 60kg 5组5次" -> {"intent": "log_workout", "confidence": 0.95, "reason": "recording workout with exercises/sets/reps"}
"帮我制定一个减脂计划" -> {"intent": "create_plan", "confidence": 0.95, "reason": "explicit request to create a plan"}
"新手应该怎么开始健身" -> {"intent": "fitness_qa", "confidence": 0.9, "reason": "asking for fitness knowledge/advice"}
"这周练了几天" -> {"intent": "query_history", "confidence": 0.9, "reason": "querying workout history"}
"你好啊" -> {"intent": "casual_chat", "confidence": 0.95, "reason": "greeting/casual chat"}
"我想把周三的训练换成周四" -> {"intent": "update_plan", "confidence": 0.9, "reason": "modifying existing training schedule"}

User input: {user_input}

JSON:"""

# ------------------------------------------------------------------
# Layer 2: Keyword fallback
# ------------------------------------------------------------------


def keyword_fallback(user_input: str) -> tuple[str, float]:
    """
    Keyword-based intent matching when LLM is unavailable or uncertain.

    Scoring: each matched keyword adds 1 point. The highest-scoring intent wins.
    Confidence is capped at 0.65 to reflect that this is a heuristic method.
    """
    scores: dict[str, int] = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in user_input)
        if score > 0:
            scores[intent] = score

    if not scores:
        return "casual_chat", 0.3

    best_intent = max(scores, key=scores.get)
    confidence = min(scores[best_intent] / 5.0, 0.65)
    return best_intent, confidence


# ------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------


async def classify_intent(user_input: str, llm: Optional[LLMClient] = None) -> dict:
    """
    Classify user intent using two-layer routing.

    Layer 1 (primary):   LLM classification via LLMClient.chat_structured()
    Layer 2 (fallback):  keyword matching when Layer 1 fails or confidence < 0.7

    Args:
        user_input: raw user message
        llm: LLMClient instance; if None or unavailable, uses keyword fallback directly

    Returns:
        {"intent": str, "confidence": float, "reason": str}
    """
    # Layer 1: LLM Classification (when available)
    if llm and llm.is_available:
        try:
            prompt = INTENT_PROMPT.format(user_input=user_input)
            result = await llm.chat_structured(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=150,
            )
            intent = result.get("intent", "casual_chat")
            confidence = float(result.get("confidence", 0.5))
            reason = result.get("reason", "")

            # High confidence → trust LLM and return directly
            if confidence >= 0.7:
                return {"intent": intent, "confidence": confidence, "reason": reason}
        except Exception:
            # LLM call failed → fall through to keyword fallback
            pass

    # Layer 2: Keyword Fallback
    intent, confidence = keyword_fallback(user_input)
    return {"intent": intent, "confidence": confidence, "reason": "keyword_fallback"}
