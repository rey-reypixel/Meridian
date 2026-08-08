from typing import List, Dict, Optional
import numpy as np
from app.config import settings
from app.services.embeddings import embedding_service


class ContextTruncation:
    """Semantic context truncation using FastEmbed embeddings"""

    def __init__(self):
        self.enabled = settings.context_truncation_enabled

    def get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text, using the Redis cache on hit"""
        return embedding_service.get_embedding(text)

    def semantic_score(self, message: str, reference: str) -> float:
        """Cosine similarity between a message and a reference text"""
        if not message or not reference:
            return 0.0

        emb_a = self.get_embedding(message)
        emb_b = self.get_embedding(reference)
        return embedding_service.cosine_similarity(emb_a, emb_b)

    def truncate_context(
        self,
        messages: List[Dict[str, str]],
        relevance_threshold: Optional[float] = None,
        preserve_recent: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Truncate message context by dropping older messages that aren't
        semantically relevant to the latest message. The most recent
        `preserve_recent` messages are always kept untouched.
        """
        if not self.enabled or not messages:
            return messages

        relevance_threshold = (
            relevance_threshold if relevance_threshold is not None
            else settings.context_relevance_threshold
        )
        preserve_recent = (
            preserve_recent if preserve_recent is not None
            else settings.preserve_recent_messages
        )

        if len(messages) <= preserve_recent:
            return messages

        recent = messages[-preserve_recent:]
        older = messages[:-preserve_recent]
        anchor = messages[-1]["content"]

        kept_older = [
            msg for msg in older
            if self.semantic_score(msg["content"], anchor) >= relevance_threshold
        ]

        return kept_older + recent

    def get_compression_ratio(self, original_messages: List[Dict], truncated_messages: List[Dict]) -> float:
        """Calculate compression ratio"""
        if not original_messages:
            return 1.0
        return len(truncated_messages) / len(original_messages)


# Global instance
context_truncation = ContextTruncation()
