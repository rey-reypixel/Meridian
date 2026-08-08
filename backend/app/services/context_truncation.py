from typing import List, Dict, Any
from app.config import settings
import numpy as np


class ContextTruncation:
    """Semantic context truncation using embeddings"""

    def __init__(self):
        """Initialize FastEmbed model - Phase 2 implementation"""
        self.model = None
        self.enabled = settings.context_truncation_enabled

    def truncate_context(
        self,
        messages: List[Dict[str, str]],
        relevance_threshold: float = None,
        preserve_recent: int = None
    ) -> List[Dict[str, str]]:
        """
        Truncate message context by removing irrelevant messages

        Phase 1: Return messages as-is
        Phase 2: Implement semantic relevance scoring
        """
        if not self.enabled or relevance_threshold is None:
            return messages

        relevance_threshold = relevance_threshold or settings.context_relevance_threshold
        preserve_recent = preserve_recent or settings.preserve_recent_messages

        # Phase 1: Simple truncation - keep last N messages
        if len(messages) > preserve_recent:
            return messages[-preserve_recent:]

        return messages

    def get_compression_ratio(self, original_messages: List[Dict], truncated_messages: List[Dict]) -> float:
        """Calculate compression ratio"""
        if not original_messages:
            return 1.0
        return len(truncated_messages) / len(original_messages)


# Global instance
context_truncation = ContextTruncation()
