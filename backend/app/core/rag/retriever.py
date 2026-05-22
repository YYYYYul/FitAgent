"""
Unified RAG retriever interface.

Retrieval pipeline:
  1. Receive query string
  2. Vectorize query using the fitted TF-IDF vectorizer
  3. Compute cosine similarity against all knowledge base documents
  4. Return top-K results above the minimum score threshold
  5. If no results pass threshold → return empty list (caller should handle fallback)

Design notes:
- The retriever wraps a knowledge base + vectorizer
- The interface is deliberately simple so it can be swapped for pgvector later
- All results include a similarity score for debugging and threshold tuning
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RagSource:
    """A single retrieved knowledge source."""

    title: str
    content: str
    category: str
    score: float  # cosine similarity score [0, 1]


class Retriever:
    """
    Retrieves relevant knowledge chunks for a given query.

    Usage:
        retriever = Retriever()
        retriever.index(documents)  # called once at startup
        results = retriever.retrieve("新手怎么开始健身", top_k=3)
        # → [RagSource(...), RagSource(...), RagSource(...)]
    """

    def __init__(self, min_score: float = 0.05):
        """
        Args:
            min_score: minimum cosine similarity threshold for a result to be returned.
                       Set low because TF-IDF on small corpora produces low absolute scores.
        """
        self.min_score = min_score
        self._documents: list[dict] = []  # raw document dicts
        self._vectors: list[dict[int, float]] = []  # TF-IDF vectors
        self._vectorizer = None  # fitted SimpleTfidfVectorizer
        self._indexed = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def index(self, documents: list[dict]) -> None:
        """
        Build the search index from a list of knowledge documents.

        Each document should have: title, content, category.

        This should be called once at application startup.
        The index is kept entirely in memory for fast retrieval.
        """
        from app.core.rag.embeddings import SimpleTfidfVectorizer

        self._documents = documents

        # Build corpus texts: concatenate title + content for better matching
        corpus = [f"{doc['title']} {doc['content']}" for doc in documents]

        # Fit vectorizer and transform documents
        self._vectorizer = SimpleTfidfVectorizer()
        self._vectorizer.fit(corpus)
        self._vectors = self._vectorizer.transform(corpus)
        self._indexed = True

    def retrieve(self, query: str, top_k: int = 3) -> list[RagSource]:
        """
        Retrieve the top-K most relevant knowledge chunks for a query.

        Args:
            query: user's question (natural language, Chinese)
            top_k: maximum number of results to return

        Returns:
            list of RagSource objects sorted by relevance (highest first).
            Empty list if no results pass the minimum score threshold.
        """
        if not self._indexed:
            return []

        # Vectorize query
        query_vec = self._vectorizer.transform_query(query)

        # Compute similarities
        scores = self._vectorizer.cosine_similarity(query_vec, self._vectors)

        # Collect results above threshold
        results: list[RagSource] = []
        for i, score in enumerate(scores):
            if score >= self.min_score:
                doc = self._documents[i]
                results.append(RagSource(
                    title=doc["title"],
                    content=doc["content"],
                    category=doc["category"],
                    score=round(score, 4),
                ))

        # Sort by score descending, take top-K
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    @property
    def is_indexed(self) -> bool:
        return self._indexed

    @property
    def document_count(self) -> int:
        return len(self._documents)
