import hashlib
from typing import Dict, Optional, List
import numpy as np


class EmbeddingCache:
    """In-memory embedding cache"""

    def __init__(self, max_size: int = 10000):
        self.cache: Dict[str, np.ndarray] = {}
        self.max_size = max_size

    def _hash_text(self, text: str) -> str:
        """Generate hash for text"""
        return hashlib.sha256(text.encode()).hexdigest()

    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get embedding from cache"""
        key = self._hash_text(text)
        return self.cache.get(key)

    def set_embedding(self, text: str, embedding: np.ndarray) -> None:
        """Cache an embedding"""
        if len(self.cache) >= self.max_size:
            # Simple eviction: remove oldest entries
            keys_to_remove = list(self.cache.keys())[:len(self.cache) // 4]
            for key in keys_to_remove:
                del self.cache[key]

        key = self._hash_text(text)
        self.cache[key] = embedding

    def clear(self) -> None:
        """Clear entire cache"""
        self.cache.clear()

    def size(self) -> int:
        """Get cache size"""
        return len(self.cache)


# Global instance
embedding_cache = EmbeddingCache()
