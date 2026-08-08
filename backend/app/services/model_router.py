from typing import Tuple, Dict, List, Optional
from app.config import settings
from app.services.embeddings import embedding_service


class ModelRouter:
    """Intelligent model routing based on task type and quality requirements"""

    # Canonical example prompts per task type. classify_task() embeds the
    # incoming prompt and compares it against these via cosine similarity,
    # rather than brittle keyword matching.
    TASK_EXAMPLES: Dict[str, List[str]] = {
        "classification": [
            "Classify this email as spam or not spam",
            "Categorize this support ticket by urgency",
            "Label this image as cat or dog",
            "Is this review positive or negative?",
        ],
        "summarization": [
            "Summarize this article in three sentences",
            "Give me a brief summary of this document",
            "Condense this report into key points",
        ],
        "coding": [
            "Write a Python function to sort a list",
            "Implement a binary search algorithm",
            "Generate a REST API endpoint in FastAPI",
            "Debug this JavaScript code",
        ],
        "general": [
            "What is the capital of France?",
            "Explain how photosynthesis works",
            "Tell me a joke",
            "What's the weather like today?",
        ],
    }

    # Quality scores per task/model (0-10 scale)
    QUALITY_SCORES: Dict[Tuple[str, str], float] = {
        # Classification
        ("classification", "claude-haiku"): 8.5,
        ("classification", "claude-sonnet"): 9.2,
        ("classification", "claude-opus"): 9.5,
        # Summarization
        ("summarization", "claude-haiku"): 8.0,
        ("summarization", "claude-sonnet"): 9.0,
        ("summarization", "claude-opus"): 9.3,
        # Coding
        ("coding", "claude-haiku"): 7.0,
        ("coding", "claude-sonnet"): 8.8,
        ("coding", "claude-opus"): 9.6,
        # General
        ("general", "claude-haiku"): 7.5,
        ("general", "claude-sonnet"): 8.5,
        ("general", "claude-opus"): 9.0,
    }

    # Model costs (order matters: cheapest first)
    MODEL_ORDER = ["claude-haiku", "claude-sonnet", "claude-opus"]

    def __init__(self):
        self.enabled = settings.model_routing_enabled
        self.quality_threshold = settings.quality_threshold
        self.min_confidence = settings.task_classification_min_confidence

    def classify_task(self, prompt: str) -> str:
        """Classify task from prompt via embedding similarity against TASK_EXAMPLES"""
        if not prompt:
            return "general"

        best_type = "general"
        best_score = -1.0
        for task_type, examples in self.TASK_EXAMPLES.items():
            for example in examples:
                score = embedding_service.similarity(prompt, example)
                if score > best_score:
                    best_score = score
                    best_type = task_type

        if best_score < self.min_confidence:
            return "general"
        return best_type

    def _select_for_task(
        self,
        original_model: str,
        task_type: str,
        quality_threshold: Optional[float] = None
    ) -> Tuple[str, float]:
        """Select best model for an already-classified task type"""
        if not self.enabled:
            return original_model, self.get_quality_score(task_type, original_model)

        quality_threshold = quality_threshold if quality_threshold is not None else self.quality_threshold

        # Find cheapest model meeting quality threshold
        for model in self.MODEL_ORDER:
            score = self.get_quality_score(task_type, model)
            if score >= quality_threshold:
                return model, score

        # Fallback to original model if no cheap option meets threshold
        return original_model, self.get_quality_score(task_type, original_model)

    def select_model(
        self,
        original_model: str,
        prompt: str,
        quality_threshold: Optional[float] = None,
        task_type: Optional[str] = None
    ) -> Tuple[str, float]:
        """
        Select best model for the task

        Returns:
            Tuple of (selected_model, quality_score)
        """
        task_type = task_type or self.classify_task(prompt)
        return self._select_for_task(original_model, task_type, quality_threshold)

    def get_quality_score(self, task_type: str, model: str) -> float:
        """Get quality score for task/model combination"""
        return self.QUALITY_SCORES.get((task_type, model), 7.0)

    def get_routing_decision(
        self,
        original_model: str,
        prompt: str,
        quality_threshold: Optional[float] = None,
        task_type: Optional[str] = None
    ) -> Dict[str, any]:
        """Get full routing decision info. Pass task_type if already
        classified elsewhere in the request to avoid re-embedding the prompt."""
        task_type = task_type or self.classify_task(prompt)
        selected_model, quality_score = self._select_for_task(original_model, task_type, quality_threshold)

        return {
            "original_model": original_model,
            "routed_model": selected_model,
            "task_type": task_type,
            "quality_score": quality_score,
            "was_routed": selected_model != original_model
        }


# Global instance
model_router = ModelRouter()
