import hashlib
import pickle
from typing import Optional
import numpy as np
import redis
from app.config import settings


class EmbeddingCache:
    """Redis-backed embedding cache"""

    def __init__(self):
        self.client = redis.Redis.from_url(settings.redis_url, decode_responses=False)
        self.ttl_seconds = settings.embedding_cache_ttl_seconds

    def _key(self, text: str) -> str:
        """Generate cache key for text"""
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return f"meridian:embedding:{text_hash}"

    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get embedding from cache, or None on miss"""
        raw = self.client.get(self._key(text))
        if raw is None:
            return None
        return pickle.loads(raw)

    def set_embedding(self, text: str, embedding: np.ndarray) -> None:
        """Cache an embedding with TTL"""
        self.client.set(self._key(text), pickle.dumps(embedding), ex=self.ttl_seconds)

    def clear(self) -> None:
        """Clear all cached embeddings"""
        for key in self.client.scan_iter("meridian:embedding:*"):
            self.client.delete(key)

    def size(self) -> int:
        """Count cached embeddings"""
        return sum(1 for _ in self.client.scan_iter("meridian:embedding:*"))


# Global instance
embedding_cache = EmbeddingCache()
