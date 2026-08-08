import json
import uuid
from typing import Optional, Dict, Any
import numpy as np
import redis
from app.config import settings
from app.services.embeddings import embedding_service


class ResponseCache:
    """
    Semantic cache for LLM completions. If a new prompt is close enough
    (cosine similarity) to a recently-cached prompt for the same model,
    the cached response is reused instead of calling the LLM again.

    Deliberately conservative: the similarity threshold defaults high
    (0.97) because a wrong cache hit returns a plausible-looking wrong
    answer, which is worse than a miss. Callers should also avoid caching
    high-temperature (stochastic) requests - see
    settings.response_cache_max_temperature - since reusing an old
    response instead of sampling a new one isn't obviously correct when
    variety is expected.
    """

    def __init__(self):
        self.enabled = settings.response_cache_enabled
        self.similarity_threshold = settings.response_cache_similarity_threshold
        self.max_entries_per_model = settings.response_cache_max_entries
        self.ttl_seconds = settings.response_cache_ttl_seconds
        self.redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)

    def _index_key(self, model: str) -> str:
        return f"meridian:response_cache:{model}:index"

    def _entry_key(self, model: str, entry_id: str) -> str:
        return f"meridian:response_cache:{model}:entry:{entry_id}"

    def get(self, model: str, prompt_text: str) -> Optional[Dict[str, Any]]:
        """Return the best cached response for this model if it's similar
        enough to prompt_text, else None."""
        if not self.enabled or not prompt_text:
            return None

        entry_ids = self.redis.lrange(self._index_key(model), 0, -1)
        if not entry_ids:
            return None

        prompt_embedding = embedding_service.get_embedding(prompt_text)

        best_score = -1.0
        best_entry = None
        for entry_id in entry_ids:
            raw = self.redis.get(self._entry_key(model, entry_id))
            if not raw:
                continue
            entry = json.loads(raw)
            entry_embedding = np.array(entry["embedding"], dtype=np.float32)
            score = embedding_service.cosine_similarity(prompt_embedding, entry_embedding)
            if score > best_score:
                best_score = score
                best_entry = entry

        if best_entry is not None and best_score >= self.similarity_threshold:
            return {
                "content": best_entry["content"],
                "input_tokens": best_entry["input_tokens"],
                "output_tokens": best_entry["output_tokens"],
                "similarity": round(best_score, 4),
            }

        return None

    def set(
        self,
        model: str,
        prompt_text: str,
        content: str,
        input_tokens: int,
        output_tokens: int
    ) -> None:
        """Cache a response, evicting the oldest entry for this model if over capacity."""
        if not self.enabled or not prompt_text:
            return

        entry_id = str(uuid.uuid4())
        embedding = embedding_service.get_embedding(prompt_text)
        entry = {
            "content": content,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "embedding": embedding.tolist(),
        }

        self.redis.set(self._entry_key(model, entry_id), json.dumps(entry), ex=self.ttl_seconds)

        index_key = self._index_key(model)
        self.redis.rpush(index_key, entry_id)
        self.redis.expire(index_key, self.ttl_seconds)

        size = self.redis.llen(index_key)
        if size > self.max_entries_per_model:
            excess = size - self.max_entries_per_model
            evicted = self.redis.lpop(index_key, excess)
            if evicted:
                if isinstance(evicted, str):
                    evicted = [evicted]
                for old_id in evicted:
                    self.redis.delete(self._entry_key(model, old_id))

    def size(self, model: str) -> int:
        """Count cached entries for a model"""
        return self.redis.llen(self._index_key(model))


# Global instance
response_cache = ResponseCache()
