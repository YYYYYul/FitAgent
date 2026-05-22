"""
Node: fitness_qa — answers fitness knowledge questions using RAG + LLM.

In:  state.user_input
Out: state.final_response, state.intent, state.rag_context, state.rag_sources

Data flow:
  User question
    → Retriever.retrieve(query, top_k=3)
    → [有结果] Build RAG context → LLM.chat() with context → answer + sources
    → [无结果] LLM.chat() without context → generic fitness answer
    → [LLM不可用] Build template answer from retrieval results
    → [检索也不可用] Full fallback template

RAG is ONLY used for fitness_qa — never for casual_chat, create_plan, or log_workout.
"""

from typing import Optional
from app.core.agent.state import AgentState
from app.core.agent.llm_client import LLMClient
from app.core.rag.knowledge_base import get_retriever

# System prompt for RAG-augmented answers (with knowledge base context)
RAG_SYSTEM_PROMPT = """You are FitAgent, a professional fitness knowledge assistant.

Answer the user's fitness question based on the provided knowledge base content.
Rules:
- Use the knowledge base as your primary source
- If the knowledge base doesn't fully answer the question, supplement with your own knowledge
- Never give medical diagnoses, drug recommendations, or dangerous training advice
- If unsure, recommend consulting a certified fitness trainer
- Keep answers practical, actionable, and concise (3-6 sentences)
- Cite the source titles when using specific facts from the knowledge base"""

# System prompt for LLM-only answers (no retrieval results)
LLM_ONLY_PROMPT = """You are FitAgent, a professional fitness knowledge assistant.
Answer fitness-related questions accurately and safely.
- If unsure, recommend consulting a certified trainer.
- Never give medical advice, drug recommendations, or dangerous training suggestions.
- Keep answers practical, actionable, and concise (3-5 sentences)."""


async def fitness_qa_node(state: AgentState, llm: Optional[LLMClient] = None) -> dict:
    """
    Answer fitness knowledge questions with RAG + LLM.

    Four-tier fallback strategy:
      Tier 1: RAG + LLM    — retrieval results available + LLM available
      Tier 2: LLM only     — no retrieval results, but LLM available
      Tier 3: RAG template — retrieval results available, but LLM unavailable
      Tier 4: Full fallback — neither retrieval nor LLM available
    """
    user_input = state.get("user_input", "")
    rag_context = None
    rag_sources: list[dict] = []
    rag_fallback_used = False
    fallback_reason = ""
    llm_used = False

    # ------------------------------------------------------------------
    # Step 1: RAG Retrieval
    # ------------------------------------------------------------------
    retriever = get_retriever()
    retrieved = []
    if retriever and retriever.is_indexed:
        retrieved = retriever.retrieve(user_input, top_k=3)

    # ------------------------------------------------------------------
    # Step 2: Tier 1 — RAG + LLM (best case)
    # ------------------------------------------------------------------
    if retrieved and llm and llm.is_available:
        try:
            # Build context from retrieved sources
            context_parts = []
            for i, src in enumerate(retrieved):
                context_parts.append(f"[{i+1}] {src.title}\n{src.content}")
                rag_sources.append({
                    "title": src.title,
                    "category": src.category,
                    "score": src.score,
                })
            rag_context = "\n\n".join(context_parts)

            # Call LLM with RAG context
            reply = await llm.chat(
                messages=[
                    {"role": "system", "content": RAG_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Knowledge base:\n\n{rag_context}\n\nUser question: {user_input}"},
                ],
                temperature=0.5,
                max_tokens=500,
            )
            llm_used = True

            # Append source citations
            sources_str = "、".join(s["title"] for s in rag_sources[:3])
            reply += f"\n\n📚 参考：{sources_str}"

            return {
                "final_response": reply,
                "intent": "fitness_qa",
                "rag_context": rag_context,
                "rag_sources": rag_sources,
                "requires_confirmation": False,
            }
        except Exception:
            fallback_reason = "llm_error_with_rag"
            # Fall through to Tier 3

    # ------------------------------------------------------------------
    # Step 3: Tier 2 — LLM only (no retrieval results)
    # ------------------------------------------------------------------
    if not retrieved and llm and llm.is_available:
        try:
            reply = await llm.chat(
                messages=[
                    {"role": "system", "content": LLM_ONLY_PROMPT},
                    {"role": "user", "content": user_input},
                ],
                temperature=0.5,
                max_tokens=500,
            )
            llm_used = True
            rag_fallback_used = True
            fallback_reason = "no_retrieval_results"

            return {
                "final_response": reply,
                "intent": "fitness_qa",
                "rag_context": None,
                "rag_sources": [],
                "requires_confirmation": False,
            }
        except Exception:
            fallback_reason = "llm_error_no_rag"
            # Fall through to Tier 4

    # ------------------------------------------------------------------
    # Step 4: Tier 3 — RAG template (retrieval results, no LLM)
    # ------------------------------------------------------------------
    if retrieved and not llm_used:
        rag_fallback_used = True
        fallback_reason = fallback_reason or "llm_unavailable_with_rag"

        # Build a template answer from the top retrieval results
        top = retrieved[0]
        reply = (
            f"关于「{user_input}」，根据知识库中的相关内容：\n\n"
            f"📖 {top.title}\n{top.content}\n"
        )
        if len(retrieved) > 1:
            reply += f"\n📖 {retrieved[1].title}\n{retrieved[1].content}\n"

        reply += "\n⚠️ 当前 LLM 未配置，以上为知识库检索结果。配置 API Key 后可获得更完整的回答。"

        for src in retrieved:
            rag_sources.append({
                "title": src.title,
                "category": src.category,
                "score": src.score,
            })

        return {
            "final_response": reply,
            "intent": "fitness_qa",
            "rag_context": rag_context or "",
            "rag_sources": rag_sources,
            "requires_confirmation": False,
        }

    # ------------------------------------------------------------------
    # Step 5: Tier 4 — Full fallback (no retrieval, no LLM)
    # ------------------------------------------------------------------
    rag_fallback_used = True
    fallback_reason = fallback_reason or "no_retrieval_and_no_llm"

    reply = (
        f"关于「{user_input}」，这是个很好的健身问题！\n\n"
        "目前知识库中暂未找到相关内容，LLM 也未配置。"
        "不过我可以帮你：\n"
        "• 制定个性化训练计划\n"
        "• 记录每日训练内容\n"
        "• 查看训练历史和月度复盘\n\n"
        "你可以换个方式提问，或者配置 API Key 和知识库后再次尝试。有什么我能帮你的吗？"
    )

    return {
        "final_response": reply,
        "intent": "fitness_qa",
        "rag_context": None,
        "rag_sources": [],
        "requires_confirmation": False,
    }
