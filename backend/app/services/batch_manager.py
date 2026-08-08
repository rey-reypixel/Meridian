import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import redis
from app.config import settings


class BatchManager:
    """
    Redis-backed batch processing manager. Groups requests by (model,
    task_type); once a group hits `batch_size` or sits for `batch_timeout`
    seconds, a Celery task processes the whole group in the worker process.

    State lives in Redis (not an in-memory dict) because the API process
    (backend) and the task runner (worker) are separate containers — an
    in-memory dict wouldn't be visible across them.
    """

    def __init__(self, batch_timeout_seconds: int = 5, batch_size: int = 10):
        self.batch_timeout = batch_timeout_seconds
        self.batch_size = batch_size
        self.enabled = settings.batch_processing_enabled
        self.redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)

    def _get_batch_key(self, model: str, task_type: str) -> str:
        """Generate batch key from model and task type"""
        return f"{model}:{task_type}"

    def _items_key(self, batch_key: str) -> str:
        return f"meridian:batch:{batch_key}:items"

    def _created_key(self, batch_key: str) -> str:
        return f"meridian:batch:{batch_key}:created_at"

    def _result_key(self, request_id: str) -> str:
        return f"meridian:batch:result:{request_id}"

    def add_to_batch(
        self,
        request_id: str,
        model: str,
        task_type: str,
        request_data: Dict[str, Any]
    ) -> Optional[str]:
        """Queue a request into its batch. Returns the batch_key, or None if disabled."""
        if not self.enabled:
            return None

        batch_key = self._get_batch_key(model, task_type)
        item = json.dumps({"request_id": request_id, "data": request_data})
        self.redis.rpush(self._items_key(batch_key), item)
        self.redis.set(self._created_key(batch_key), datetime.utcnow().isoformat(), nx=True)

        if self._should_process_batch(batch_key):
            from app.celery_app import process_batch_task
            process_batch_task.delay(batch_key)

        return batch_key

    def _should_process_batch(self, batch_key: str) -> bool:
        """Check if batch should be processed"""
        size = self.redis.llen(self._items_key(batch_key))
        if size >= self.batch_size:
            return True

        created_raw = self.redis.get(self._created_key(batch_key))
        if created_raw:
            created_at = datetime.fromisoformat(created_raw)
            if (datetime.utcnow() - created_at).total_seconds() >= self.batch_timeout:
                return True

        return False

    def pop_batch(self, batch_key: str) -> List[Dict[str, Any]]:
        """Atomically pop all queued items for a batch. Called by the Celery task."""
        items_key = self._items_key(batch_key)
        raw_items = self.redis.lrange(items_key, 0, -1)
        self.redis.delete(items_key)
        self.redis.delete(self._created_key(batch_key))
        return [json.loads(item) for item in raw_items]

    def store_result(self, request_id: str, result: Dict[str, Any]) -> None:
        """Store a single request's batched result for its HTTP handler to collect"""
        self.redis.set(self._result_key(request_id), json.dumps(result), ex=60)

    def wait_for_result(
        self,
        request_id: str,
        batch_key: str,
        timeout: float = 15.0,
        poll_interval: float = 0.2
    ) -> Optional[Dict[str, Any]]:
        """
        Block until this request's batched result appears. Meant to be run
        via a threadpool (it's a blocking sleep loop), not awaited directly.

        There's no periodic Celery beat flushing batches on a timer (see
        Phase 2 plan) — a batch only gets checked when a new request arrives
        for it. So if this request's own wait times out, force a flush of
        its batch inline as a safety net rather than leaving it hanging.
        """
        result_key = self._result_key(request_id)
        deadline = time.time() + timeout

        while time.time() < deadline:
            raw = self.redis.get(result_key)
            if raw:
                self.redis.delete(result_key)
                return json.loads(raw)
            time.sleep(poll_interval)

        from app.celery_app import process_batch_task
        process_batch_task(batch_key)  # run inline, no worker round-trip

        raw = self.redis.get(result_key)
        if raw:
            self.redis.delete(result_key)
            return json.loads(raw)

        return None

    def get_batch_info(self, batch_key: str) -> Dict[str, Any]:
        """Get info about a batch"""
        items_key = self._items_key(batch_key)
        raw_items = self.redis.lrange(items_key, 0, -1)
        return {
            "batch_key": batch_key,
            "size": len(raw_items),
            "created_at": self.redis.get(self._created_key(batch_key)),
            "requests": [json.loads(item)["request_id"] for item in raw_items]
        }

    def clear_expired_batches(self, timeout_seconds: Optional[float] = None) -> int:
        """Force-flush any batches whose timeout has elapsed. Returns count flushed."""
        timeout = timeout_seconds if timeout_seconds is not None else self.batch_timeout
        prefix, suffix = "meridian:batch:", ":created_at"
        removed = 0

        for created_key in self.redis.scan_iter(f"{prefix}*{suffix}"):
            created_raw = self.redis.get(created_key)
            if not created_raw:
                continue
            created_at = datetime.fromisoformat(created_raw)
            if (datetime.utcnow() - created_at).total_seconds() >= timeout:
                batch_key = created_key[len(prefix):-len(suffix)]
                from app.celery_app import process_batch_task
                process_batch_task.delay(batch_key)
                removed += 1

        return removed


# Global instance
batch_manager = BatchManager()
