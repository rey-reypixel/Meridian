from typing import Optional
import numpy as np
from fastembed import TextEmbedding
from app.services.cache import embedding_cache


class EmbeddingService:
    """
    Shared FastEmbed model + Redis-cached embedding lookup.

    Used by context truncation, task classification, and semantic response
    caching - all three need "embed this text, compare via cosine
    similarity" and none of them should load their own copy of the model.
    """

    _model: Optional[TextEmbedding] = None

    @property
    def model(self) -> TextEmbedding:
        """Lazily load the embedding model on first use (expensive, load once)"""
        if EmbeddingService._model is None:
            EmbeddingService._model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        return EmbeddingService._model

    def get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text, using the Redis cache on hit"""
        cached = embedding_cache.get_embedding(text)
        if cached is not None:
            return cached

        embedding = next(self.model.embed([text]))
        embedding_cache.set_embedding(text, embedding)
        return embedding

    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def similarity(self, text_a: str, text_b: str) -> float:
        """Cosine similarity between two texts (embeds + caches both)"""
        if not text_a or not text_b:
            return 0.0
        return self.cosine_similarity(self.get_embedding(text_a), self.get_embedding(text_b))


# Global instance
embedding_service = EmbeddingService()
