"""
Lightweight TF-IDF text vectorizer — pure Python, no external dependencies.

WHY this approach:
- Works with SQLite (no pgvector required)
- Zero external dependencies for retrieval
- Good enough for ~40 documents in the knowledge base
- Easy to swap for sentence-transformers or pgvector later via the same interface

Vectorization pipeline:
  1. Tokenize: split text into words (Chinese: character-level bigrams + whole words)
  2. Build vocabulary from all documents
  3. Compute TF (term frequency per document)
  4. Compute IDF (inverse document frequency across corpus)
  5. TF-IDF = TF × IDF
  6. Cosine similarity for query-document matching

Reference: This is a simplified version of sklearn's TfidfVectorizer,
           optimized for small Chinese fitness knowledge bases.
"""

import re
import math
from collections import Counter


class SimpleTfidfVectorizer:
    """
    Lightweight TF-IDF vectorizer for Chinese fitness text.

    Usage:
        vec = SimpleTfidfVectorizer()
        vec.fit(documents)              # build vocabulary + IDF
        vectors = vec.transform(documents)  # get TF-IDF vectors
        query_vec = vec.transform_query("新手怎么练")  # vectorize a query
        scores = vec.cosine_similarity(query_vec, doc_vectors)  # rank docs
    """

    def __init__(self):
        self.vocabulary: dict[str, int] = {}  # word → index
        self.idf: dict[str, float] = {}       # word → IDF value
        self._fitted = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(self, documents: list[str]) -> "SimpleTfidfVectorizer":
        """
        Build vocabulary and compute IDF values from a corpus of documents.

        Args:
            documents: list of text strings to build vocabulary from
        """
        # Step 1: Tokenize all documents
        tokenized = [self._tokenize(doc) for doc in documents]

        # Step 2: Build vocabulary (all unique tokens across all docs)
        vocab_set: set[str] = set()
        for tokens in tokenized:
            vocab_set.update(tokens)
        self.vocabulary = {word: i for i, word in enumerate(sorted(vocab_set))}

        # Step 3: Compute IDF = log((1 + N) / (1 + df)) + 1  (smooth IDF)
        n_docs = len(documents)
        df: dict[str, int] = Counter()
        for tokens in tokenized:
            unique_tokens = set(tokens)
            for token in unique_tokens:
                df[token] += 1

        for word, idx in self.vocabulary.items():
            self.idf[word] = math.log((1 + n_docs) / (1 + df.get(word, 0))) + 1

        self._fitted = True
        return self

    def transform(self, documents: list[str]) -> list[dict[int, float]]:
        """
        Convert documents to TF-IDF sparse vectors.

        Each vector is a dict {word_index: tfidf_value} for non-zero entries only.

        Returns:
            list of sparse vectors (one per document)
        """
        if not self._fitted:
            raise RuntimeError("Vectorizer not fitted. Call fit() first.")

        vectors: list[dict[int, float]] = []
        for doc in documents:
            tokens = self._tokenize(doc)
            tf = Counter(tokens)
            vec: dict[int, float] = {}
            for word, count in tf.items():
                if word in self.vocabulary:
                    idx = self.vocabulary[word]
                    tf_val = count / len(tokens) if tokens else 0
                    vec[idx] = tf_val * self.idf.get(word, 1.0)
            vectors.append(vec)
        return vectors

    def transform_query(self, query: str) -> dict[int, float]:
        """
        Vectorize a single query string.
        Uses the same vocabulary as the fitted corpus.
        """
        vectors = self.transform([query])
        return vectors[0] if vectors else {}

    def cosine_similarity(
        self, query_vec: dict[int, float], doc_vectors: list[dict[int, float]]
    ) -> list[float]:
        """
        Compute cosine similarity between a query vector and multiple document vectors.

        Returns:
            list of similarity scores [0, 1], one per document
        """
        query_norm = math.sqrt(sum(v ** 2 for v in query_vec.values()))
        if query_norm == 0:
            return [0.0] * len(doc_vectors)

        scores: list[float] = []
        for doc_vec in doc_vectors:
            # Dot product
            dot = 0.0
            for idx, q_val in query_vec.items():
                if idx in doc_vec:
                    dot += q_val * doc_vec[idx]

            doc_norm = math.sqrt(sum(v ** 2 for v in doc_vec.values()))
            if doc_norm == 0:
                scores.append(0.0)
            else:
                scores.append(dot / (query_norm * doc_norm))
        return scores

    # ------------------------------------------------------------------
    # Tokenization (Chinese text optimized)
    # ------------------------------------------------------------------

    def _tokenize(self, text: str) -> list[str]:
        """
        Tokenize Chinese text into a mix of:
        - Individual Chinese characters (character-level features)
        - Chinese character bigrams (captures common 2-char words like 训练, 肌肉)
        - English/ASCII words (lowercased)
        - Numbers preserved as-is

        This simple tokenization works well for short Chinese fitness texts
        where precise word segmentation isn't critical — the TF-IDF weighting
        naturally emphasizes distinctive terms.
        """
        tokens: list[str] = []

        # Extract Chinese characters
        chinese_chars = re.findall(r'[一-鿿]', text)

        # Individual characters
        tokens.extend(chinese_chars)

        # Character bigrams (captures word-level semantics)
        for i in range(len(chinese_chars) - 1):
            tokens.append(chinese_chars[i] + chinese_chars[i + 1])

        # Extract English/ASCII words
        english_words = re.findall(r'[a-zA-Z]+', text.lower())
        tokens.extend(english_words)

        # Extract numbers
        numbers = re.findall(r'\d+', text)
        tokens.extend(numbers)

        return tokens
