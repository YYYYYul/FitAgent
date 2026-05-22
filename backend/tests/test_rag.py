"""Tests for RAG module: retriever, embeddings, knowledge base."""

import pytest
from app.core.rag.seed_data import SEED_ENTRIES
from app.core.rag.embeddings import SimpleTfidfVectorizer
from app.core.rag.retriever import Retriever
from app.core.rag.knowledge_base import init_knowledge_base, get_retriever, get_knowledge_stats


class TestSeedData:
    """Verify seed data quality."""

    def test_has_10_categories(self):
        categories = set(e["category"] for e in SEED_ENTRIES)
        assert len(categories) == 10

    def test_each_category_has_3_to_5_entries(self):
        from collections import Counter
        cat_counts = Counter(e["category"] for e in SEED_ENTRIES)
        for cat, count in cat_counts.items():
            assert 3 <= count <= 5, f"Category '{cat}' has {count} entries (expected 3-5)"

    def test_all_entries_have_required_fields(self):
        for entry in SEED_ENTRIES:
            assert "title" in entry
            assert "content" in entry
            assert "category" in entry
            assert len(entry["title"]) > 0
            assert len(entry["content"]) > 20  # meaningful content

    def test_no_medical_diagnosis(self):
        forbidden = ["诊断", "治疗", "处方", "药物", "手术"]
        for entry in SEED_ENTRIES:
            for word in forbidden:
                assert word not in entry["content"], f"'{word}' found in '{entry['title']}'"


class TestTfidfVectorizer:
    """Verify TF-IDF vectorizer."""

    def test_fit_and_transform(self):
        docs = ["新手应该如何开始健身训练", "减脂需要控制饮食和有氧运动", "增肌需要力量训练和蛋白质"]
        vec = SimpleTfidfVectorizer()
        vec.fit(docs)
        vectors = vec.transform(docs)
        assert len(vectors) == 3
        # Each vector should have some non-zero entries
        for v in vectors:
            assert len(v) > 0

    def test_empty_vocabulary_on_empty_corpus(self):
        vec = SimpleTfidfVectorizer()
        vec.fit(["", ""])
        vectors = vec.transform([""])
        assert len(vectors) == 1
        assert len(vectors[0]) == 0  # no tokens → empty vector

    def test_cosine_similarity_self_is_one(self):
        docs = ["新手训练指南", "减脂训练计划"]
        vec = SimpleTfidfVectorizer()
        vec.fit(docs)
        vectors = vec.transform(docs)
        query_vec = vec.transform_query("新手训练指南")
        scores = vec.cosine_similarity(query_vec, vectors)
        # First doc should match better than second
        assert scores[0] > scores[1]

    def test_transform_before_fit_raises(self):
        vec = SimpleTfidfVectorizer()
        with pytest.raises(RuntimeError):
            vec.transform(["some text"])


class TestRetriever:
    """Verify retriever integration."""

    @pytest.fixture
    def sample_docs(self):
        return [
            {"title": "新手训练原则", "content": "新手应该从基础动作开始，每周训练3次", "category": "beginner"},
            {"title": "减脂方法", "content": "减脂需要热量赤字和有氧运动", "category": "fat_loss"},
            {"title": "增肌训练", "content": "增肌需要力量训练和蛋白质摄入", "category": "muscle_gain"},
        ]

    def test_retrieve_returns_top_k(self, sample_docs):
        r = Retriever()
        r.index(sample_docs)
        results = r.retrieve("新手怎么训练", top_k=2)
        assert len(results) <= 2
        assert len(results) > 0
        # Top result should be about 新手
        assert "新手" in results[0].title

    def test_retrieve_respects_min_score(self, sample_docs):
        r = Retriever(min_score=0.99)  # very high threshold
        r.index(sample_docs)
        results = r.retrieve("新手怎么训练", top_k=3)
        # With such a high threshold, nothing should pass
        assert len(results) == 0

    def test_retrieve_returns_empty_when_not_indexed(self):
        r = Retriever()
        results = r.retrieve("anything")
        assert results == []

    def test_all_results_have_scores(self, sample_docs):
        r = Retriever()
        r.index(sample_docs)
        results = r.retrieve("训练", top_k=3)
        for src in results:
            assert 0 <= src.score <= 1
            assert src.title
            assert src.content
            assert src.category


class TestKnowledgeBase:
    """Verify knowledge base singleton."""

    def test_init_creates_retriever(self):
        retriever = init_knowledge_base()
        assert retriever is not None
        assert retriever.is_indexed
        assert retriever.document_count == len(SEED_ENTRIES)

    def test_get_retriever_after_init(self):
        init_knowledge_base()
        r = get_retriever()
        assert r is not None
        assert r.is_indexed

    def test_stats_after_init(self):
        init_knowledge_base()
        stats = get_knowledge_stats()
        assert stats["indexed"] is True
        assert stats["document_count"] == len(SEED_ENTRIES)
        assert len(stats["categories"]) == 10

    def test_retrieve_real_data(self):
        init_knowledge_base()
        r = get_retriever()
        results = r.retrieve("新手怎么开始健身", top_k=3)
        assert len(results) > 0
        # Top result should be about beginner principles
        assert any("新手" in src.title for src in results)
