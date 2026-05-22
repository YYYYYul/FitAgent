"""
Node: casual_chat — handles greetings, small talk, and off-topic conversation.

In:  state.user_input, state.user_profile
Out: state.final_response, state.intent

Uses LLMClient.chat() when available. Falls back to template responses when no API key.
No tools, no RAG — this is the simplest node in the graph.
"""

from app.core.agent.state import AgentState
from app.core.agent.llm_client import LLMClient
from typing import Optional

SYSTEM_PROMPT = """You are FitAgent, a professional fitness assistant. You help users with:
- Creating personalized training plans
- Recording and tracking workouts
- Answering fitness knowledge questions
- Providing motivation and encouragement

Keep responses friendly, concise (2-4 sentences for casual chat), and fitness-oriented.
If the user asks about something outside fitness, gently steer them back to fitness topics."""


async def casual_chat_node(state: AgentState, llm: Optional[LLMClient] = None) -> dict:
    """
    Handle casual conversation with LLM (or template fallback).

    When LLM is available: generates a natural, context-aware response.
    When LLM is unavailable: uses keyword-triggered template responses.
    """
    user_input = state.get("user_input", "")
    user_profile = state.get("user_profile")

    # Build context for LLM
    if llm and llm.is_available:
        try:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            # Add user context if available
            if user_profile and user_profile.get("display_name"):
                messages.append({
                    "role": "system",
                    "content": f"Current user: {user_profile['display_name']}. "
                               f"Goal: {user_profile.get('goal', 'not set')}. "
                               f"Be personal and encouraging.",
                })
            messages.append({"role": "user", "content": user_input})

            reply = await llm.chat(messages=messages, max_tokens=300)
            return {
                "final_response": reply,
                "intent": "casual_chat",
                "requires_confirmation": False,
            }
        except Exception:
            # LLM call failed → fallback to template
            pass

    # Template fallback (no LLM available or LLM error)
    greetings = ["你好", "嗨", "hey", "hello", "hi", "在吗", "早", "晚上好"]
    if any(g in user_input.lower() for g in greetings):
        reply = "你好！我是 FitAgent，你的专属健身助手。我可以帮你制定训练计划、记录训练内容、回答健身问题。有什么需要吗？"
    else:
        reply = "收到你的消息！如果你想了解健身知识、制定训练计划、或记录今天的训练，随时告诉我。"

    return {
        "final_response": reply,
        "intent": "casual_chat",
        "requires_confirmation": False,
    }
