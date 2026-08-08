from typing import Tuple, Dict, List, Optional
from app.config import settings


class ModelRouter:
    """Intelligent model routing based on task type and quality requirements"""

    # Task classification patterns
    TASK_PATTERNS: Dict[str, List[str]] = {
        "classification": ["classify", "categorize", "label", "detect", "identify"],
        "summarization": ["summarize", "summary", "brief", "condense"],
        "coding": ["code", "write", "generate", "function", "implement"],
        "general": []
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

    def classify_task(self, prompt: str) -> str:
        """Classify task from prompt using keyword matching"""
        prompt_lower = prompt.lower()

        for task_type, keywords in self.TASK_PATTERNS.items():
            if task_type == "general":
                continue
            if any(keyword in prompt_lower for keyword in keywords):
                return task_type

        return "general"

    def select_model(
        self,
        original_model: str,
        prompt: str,
        quality_threshold: Optional[float] = None
    ) -> Tuple[str, float]:
        """
        Select best model for the task

        Returns:
            Tuple of (selected_model, quality_score)
        """
        if not self.enabled:
            return original_model, self.get_quality_score(original_model, "general")

        quality_threshold = quality_threshold or self.quality_threshold
        task_type = self.classify_task(prompt)

        # Find cheapest model meeting quality threshold
        for model in self.MODEL_ORDER:
            score = self.get_quality_score(task_type, model)
            if score >= quality_threshold:
                return model, score

        # Fallback to original model if no cheap option meets threshold
        return original_model, self.get_quality_score(task_type, original_model)

    def get_quality_score(self, task_type: str, model: str) -> float:
        """Get quality score for task/model combination"""
        return self.QUALITY_SCORES.get((task_type, model), 7.0)

    def get_routing_decision(self, original_model: str, prompt: str) -> Dict[str, any]:
        """Get full routing decision info"""
        selected_model, quality_score = self.select_model(original_model, prompt)
        task_type = self.classify_task(prompt)

        return {
            "original_model": original_model,
            "routed_model": selected_model,
            "task_type": task_type,
            "quality_score": quality_score,
            "was_routed": selected_model != original_model
        }


# Global instance
model_router = ModelRouter()
