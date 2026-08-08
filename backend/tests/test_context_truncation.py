import pytest
import numpy as np
from app.services.context_truncation import ContextTruncation


def make_truncator(embeddings: dict) -> ContextTruncation:
    """Build a ContextTruncation with a fake embedder so tests don't need a
    real FastEmbed model load or a live Redis cache."""
    ct = ContextTruncation()
    ct.enabled = True
    ct.get_embedding = lambda text: embeddings[text]
    return ct


class TestContextTruncation:
    def test_disabled_returns_messages_unchanged(self):
        ct = make_truncator({})
        ct.enabled = False
        messages = [{"role": "user", "content": f"msg{i}"} for i in range(10)]
        result = ct.truncate_context(messages, relevance_threshold=0.5, preserve_recent=2)
        assert result == messages

    def test_within_preserve_recent_returns_all_untouched(self):
        ct = make_truncator({})
        messages = [{"role": "user", "content": f"msg{i}"} for i in range(3)]
        result = ct.truncate_context(messages, relevance_threshold=0.9, preserve_recent=5)
        assert result == messages

    def test_drops_low_relevance_older_messages(self):
        embeddings = {
            "old irrelevant": np.array([1.0, 0.0]),
            "old relevant": np.array([0.0, 1.0]),
            "recent 1": np.array([0.0, 1.0]),
            "recent 2": np.array([0.0, 1.0]),
            "latest": np.array([0.0, 1.0]),
        }
        ct = make_truncator(embeddings)
        messages = [
            {"role": "user", "content": "old irrelevant"},
            {"role": "user", "content": "old relevant"},
            {"role": "user", "content": "recent 1"},
            {"role": "user", "content": "recent 2"},
            {"role": "user", "content": "latest"},
        ]
        result = ct.truncate_context(messages, relevance_threshold=0.5, preserve_recent=3)
        contents = [m["content"] for m in result]

        assert "old irrelevant" not in contents
        assert "old relevant" in contents
        assert contents[-3:] == ["recent 1", "recent 2", "latest"]

    def test_preserve_recent_always_kept_even_if_irrelevant(self):
        embeddings = {
            "unrelated recent": np.array([1.0, 0.0]),
            "latest": np.array([0.0, 1.0]),
        }
        ct = make_truncator(embeddings)
        messages = [
            {"role": "user", "content": "unrelated recent"},
            {"role": "user", "content": "latest"},
        ]
        # preserve_recent=2 covers the whole list, so nothing is even scored
        result = ct.truncate_context(messages, relevance_threshold=0.9, preserve_recent=2)
        assert result == messages

    def test_semantic_score_identical_vectors(self):
        ct = make_truncator({"a": np.array([1.0, 2.0]), "b": np.array([1.0, 2.0])})
        assert ct.semantic_score("a", "b") == pytest.approx(1.0)

    def test_semantic_score_orthogonal_vectors(self):
        ct = make_truncator({"a": np.array([1.0, 0.0]), "b": np.array([0.0, 1.0])})
        assert ct.semantic_score("a", "b") == pytest.approx(0.0, abs=1e-9)

    def test_semantic_score_empty_text_returns_zero(self):
        ct = make_truncator({})
        assert ct.semantic_score("", "something") == 0.0
        assert ct.semantic_score("something", "") == 0.0

    def test_compression_ratio(self):
        ct = make_truncator({})
        original = [{"content": "a"}, {"content": "b"}, {"content": "c"}, {"content": "d"}]
        truncated = [{"content": "c"}, {"content": "d"}]
        assert ct.get_compression_ratio(original, truncated) == 0.5

    def test_compression_ratio_empty_original(self):
        ct = make_truncator({})
        assert ct.get_compression_ratio([], []) == 1.0
