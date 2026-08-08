import pytest
import fakeredis
import numpy as np
from unittest.mock import patch
from app.services.response_cache import ResponseCache

FAKE_EMBEDDINGS = {
    "prompt A": np.array([1.0, 0.0]),
    "prompt A near-duplicate": np.array([0.99, 0.01]),
    "prompt B unrelated": np.array([0.0, 1.0]),
}


def fake_get_embedding(text):
    return FAKE_EMBEDDINGS.get(text, np.array([0.5, 0.5]))


@pytest.fixture
def rc():
    cache = ResponseCache()
    cache.enabled = True
    cache.similarity_threshold = 0.9
    cache.max_entries_per_model = 3
    cache.redis = fakeredis.FakeRedis(decode_responses=True)
    return cache


@pytest.fixture(autouse=True)
def mock_embedding():
    with patch("app.services.response_cache.embedding_service.get_embedding", side_effect=fake_get_embedding):
        yield


class TestResponseCache:
    def test_miss_on_empty_cache(self, rc):
        assert rc.get("claude-haiku", "prompt A") is None

    def test_set_then_exact_match_hit(self, rc):
        rc.set("claude-haiku", "prompt A", "the answer", 10, 5)
        result = rc.get("claude-haiku", "prompt A")
        assert result is not None
        assert result["content"] == "the answer"
        assert result["input_tokens"] == 10
        assert result["output_tokens"] == 5

    def test_near_duplicate_hits_above_threshold(self, rc):
        rc.set("claude-haiku", "prompt A", "the answer", 10, 5)
        result = rc.get("claude-haiku", "prompt A near-duplicate")
        assert result is not None
        assert result["content"] == "the answer"

    def test_dissimilar_prompt_misses(self, rc):
        rc.set("claude-haiku", "prompt A", "the answer", 10, 5)
        result = rc.get("claude-haiku", "prompt B unrelated")
        assert result is None

    def test_per_model_isolation(self, rc):
        rc.set("claude-haiku", "prompt A", "haiku answer", 10, 5)
        # same prompt text, different model - must not hit
        result = rc.get("claude-sonnet", "prompt A")
        assert result is None

    def test_disabled_returns_none_and_does_not_store(self, rc):
        rc.enabled = False
        rc.set("claude-haiku", "prompt A", "the answer", 10, 5)
        assert rc.get("claude-haiku", "prompt A") is None
        assert rc.size("claude-haiku") == 0

    def test_fifo_eviction_at_max_entries(self, rc):
        for i in range(5):
            rc.set("claude-haiku", f"prompt {i}", f"answer {i}", 1, 1)

        assert rc.size("claude-haiku") == 3

    def test_size_counts_entries(self, rc):
        rc.set("claude-haiku", "prompt A", "the answer", 10, 5)
        assert rc.size("claude-haiku") == 1
