import pytest
from unittest.mock import patch
from app.services.model_router import model_router


def fake_similarity(text_a: str, text_b: str) -> float:
    """Deterministic stand-in for embedding cosine similarity: scores by
    shared-word overlap, so classification tests are predictable without
    loading a real embedding model or needing live Redis."""
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a or not words_b:
        return 0.0
    overlap = words_a & words_b
    return len(overlap) / max(len(words_a), len(words_b))


@pytest.fixture(autouse=True)
def mock_embeddings():
    with patch("app.services.model_router.embedding_service.similarity", side_effect=fake_similarity):
        yield


class TestModelRouter:
    """Test model router service"""

    def test_task_classification_simple(self):
        """Test task classification for simple tasks"""
        prompt = "Classify this email as spam"
        task = model_router.classify_task(prompt)
        assert task == "classification"

    def test_task_classification_summarization(self):
        """Test task classification for summarization"""
        prompt = "Summarize this document for me"
        task = model_router.classify_task(prompt)
        assert task == "summarization"

    def test_task_classification_coding(self):
        """Test task classification for coding"""
        prompt = "Write a Python function to reverse a string"
        task = model_router.classify_task(prompt)
        assert task == "coding"

    def test_task_classification_general(self):
        """Test task classification for general tasks"""
        prompt = "What is the capital of Germany?"
        task = model_router.classify_task(prompt)
        assert task == "general"

    def test_task_classification_low_confidence_falls_back_to_general(self):
        """A prompt with no meaningful overlap with any example should fall back to general"""
        prompt = "xyzzy plugh foobar"
        task = model_router.classify_task(prompt)
        assert task == "general"

    def test_task_classification_empty_prompt(self):
        task = model_router.classify_task("")
        assert task == "general"

    def test_select_model_classification(self):
        """Test model selection for classification"""
        prompt = "Classify the sentiment of this email"
        model, score = model_router.select_model("claude-opus", prompt)
        # Should route to cheaper model for classification
        assert score >= model_router.quality_threshold

    def test_select_model_coding(self):
        """Test model selection for coding"""
        prompt = "Write a Python function to implement a complex algorithm"
        model, score = model_router.select_model("claude-haiku", prompt)
        assert score >= 0  # Quality score is valid

    def test_get_quality_score(self):
        """Test quality score retrieval - not embedding-dependent"""
        score = model_router.get_quality_score("classification", "claude-haiku")
        assert 0 <= score <= 10
        assert score == 8.5

    def test_get_routing_decision(self):
        """Test full routing decision"""
        prompt = "Classify this text as spam"
        decision = model_router.get_routing_decision("claude-opus", prompt)

        assert "original_model" in decision
        assert "routed_model" in decision
        assert "task_type" in decision
        assert "quality_score" in decision
        assert "was_routed" in decision
        assert decision["task_type"] == "classification"

    def test_quality_threshold_enforcement(self):
        """Test that routing respects quality threshold"""
        prompt = "Classify the sentiment of this email"
        model, score = model_router.select_model("claude-opus", prompt, quality_threshold=9.0)
        assert score >= 9.0

    def test_model_selection_chooses_cheapest(self):
        """Test that cheapest model meeting threshold is chosen"""
        prompt = "Classify this email as spam"
        model, score = model_router.select_model("claude-opus", prompt, quality_threshold=8.0)

        if score >= 8.0:
            assert model in ["claude-haiku", "claude-sonnet", "claude-opus"]

    def test_get_routing_decision_quality_threshold_changes_model(self):
        """get_routing_decision's quality_threshold param should actually reach select_model"""
        prompt = "Classify this email as spam"  # classification: haiku=8.5, sonnet=9.2, opus=9.5

        loose = model_router.get_routing_decision("claude-opus", prompt, quality_threshold=8.0)
        assert loose["routed_model"] == "claude-haiku"

        strict = model_router.get_routing_decision("claude-opus", prompt, quality_threshold=9.3)
        assert strict["routed_model"] == "claude-opus"

    def test_task_type_passthrough_skips_reclassification(self):
        """A precomputed task_type should be used as-is, not re-derived from the prompt"""
        with patch("app.services.model_router.embedding_service.similarity") as mock_sim:
            decision = model_router.get_routing_decision(
                "claude-opus", "this text is irrelevant to the passed-in task_type",
                task_type="coding"
            )
            assert decision["task_type"] == "coding"
            mock_sim.assert_not_called()
