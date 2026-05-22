"""
MCP Adapter: search_fitness_knowledge — wraps core/rag/retriever.py.

WHY this is a key MCP + RAG demo point:
  External Agents (Claude Desktop) can search FitAgent's curated fitness
  knowledge base directly, getting structured results with relevance scores.
  The MCP tool only does retrieval — the calling Agent decides how to use
  the results (unlike the Web Chat fitness_qa node which also calls LLM).
"""

from app.core.rag.knowledge_base import get_retriever, init_knowledge_base


async def handle_search_fitness_knowledge(arguments: dict) -> dict:
    """
    Handle MCP 'search_fitness_knowledge' tool call — RAG retrieval only.

    Args:
        arguments: {query: str, top_k?: int (default 3)}

    Returns:
        {success, query, results: [{title, content, category, score}], result_count, source}
    """
    # Step 1: Validate query
    query = arguments.get("query", "").strip()
    if not query:
        return {
            "success": False,
            "error": "Missing required argument: query (the fitness question to search for).",
            "source": "mcp",
        }

    # Step 2: Validate top_k
    top_k = arguments.get("top_k", 3)
    try:
        top_k = int(top_k)
        if top_k < 1 or top_k > 10:
            top_k = 3
    except (ValueError, TypeError):
        top_k = 3

    # Step 3: Call RAG retriever (auto-init if needed)
    retriever = get_retriever()
    if not retriever or not retriever.is_indexed:
        retriever = init_knowledge_base()
    if not retriever or not retriever.is_indexed:
        return {
            "success": False,
            "error": "Knowledge base failed to initialize.",
            "source": "mcp",
        }

    try:
        results = retriever.retrieve(query, top_k=top_k)
    except Exception as e:
        return {
            "success": False,
            "error": f"Retrieval failed: {str(e)}",
            "source": "mcp",
        }

    # Step 4: Format results
    return {
        "success": True,
        "query": query,
        "results": [
            {
                "title": r.title,
                "content": r.content,
                "category": r.category,
                "score": r.score,
            }
            for r in results
        ],
        "result_count": len(results),
        "source": "mcp",
    }
