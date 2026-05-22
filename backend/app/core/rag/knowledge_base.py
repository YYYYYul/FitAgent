"""
Knowledge base loader and singleton manager.

Responsible for:
- Loading seed data at application startup
- Building the retrieval index
- Providing a singleton Retriever instance to all callers

Usage:
    # At app startup:
    init_knowledge_base()

    # In fitness_qa node:
    from app.core.rag.knowledge_base import get_retriever
    retriever = get_retriever()
    results = retriever.retrieve("新手怎么开始健身")
"""

from app.core.rag.seed_data import SEED_ENTRIES
from app.core.rag.retriever import Retriever

# Module-level singleton
_retriever: Retriever | None = None
_initialized = False


def init_knowledge_base() -> Retriever:
    """
    Initialize the knowledge base with seed data.

    Should be called once at application startup.
    Safe to call multiple times — subsequent calls are no-ops.

    Returns:
        The initialized Retriever instance
    """
    global _retriever, _initialized

    if _initialized and _retriever is not None:
        return _retriever

    # Convert seed entries to retriever-compatible format
    documents = [
        {
            "title": entry["title"],
            "content": entry["content"],
            "category": entry["category"],
        }
        for entry in SEED_ENTRIES
    ]

    _retriever = Retriever()
    _retriever.index(documents)
    _initialized = True

    return _retriever


def get_retriever() -> Retriever | None:
    """
    Get the singleton Retriever instance.

    Returns None if init_knowledge_base() has not been called yet.
    Callers should handle None gracefully.
    """
    return _retriever


def get_knowledge_stats() -> dict:
    """Return statistics about the loaded knowledge base."""
    if not _retriever or not _retriever.is_indexed:
        return {"indexed": False, "document_count": 0}

    categories: dict[str, int] = {}
    for entry in SEED_ENTRIES:
        cat = entry["category"]
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "indexed": True,
        "document_count": _retriever.document_count,
        "categories": categories,
        "retrieval_method": "TF-IDF + Cosine Similarity (in-memory)",
    }
