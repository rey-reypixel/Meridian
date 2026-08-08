from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio
from app.config import settings


class BatchManager:
    """Batch processing manager for grouping similar requests"""

    def __init__(self, batch_timeout_seconds: int = 5, batch_size: int = 10):
        self.batch_timeout = batch_timeout_seconds
        self.batch_size = batch_size
        self.batches: Dict[str, List[Dict[str, Any]]] = {}
        self.batch_timers: Dict[str, datetime] = {}
        self.enabled = settings.batch_processing_enabled

    def _get_batch_key(self, model: str, task_type: str) -> str:
        """Generate batch key from model and task type"""
        return f"{model}:{task_type}"

    async def add_to_batch(
        self,
        request_id: str,
        model: str,
        task_type: str,
        request_data: Dict[str, Any]
    ) -> str:
        """
        Add request to batch

        Returns:
            batch_id
        """
        if not self.enabled:
            return None

        batch_key = self._get_batch_key(model, task_type)

        if batch_key not in self.batches:
            self.batches[batch_key] = []
            self.batch_timers[batch_key] = datetime.now()

        self.batches[batch_key].append({
            "request_id": request_id,
            "data": request_data
        })

        # Check if batch should be processed
        if self._should_process_batch(batch_key):
            await self.process_batch(batch_key)

        return batch_key

    def _should_process_batch(self, batch_key: str) -> bool:
        """Check if batch should be processed"""
        batch = self.batches.get(batch_key, [])

        # Process if batch size reached
        if len(batch) >= self.batch_size:
            return True

        # Process if timeout reached
        if batch_key in self.batch_timers:
            elapsed = (datetime.now() - self.batch_timers[batch_key]).total_seconds()
            if elapsed >= self.batch_timeout:
                return True

        return False

    async def process_batch(self, batch_key: str) -> List[str]:
        """
        Process batch of requests

        Phase 1: Simple grouping
        Phase 2: Actual batch API calls
        """
        if batch_key not in self.batches:
            return []

        batch = self.batches.pop(batch_key)
        self.batch_timers.pop(batch_key, None)

        # Phase 1: Return request IDs (Phase 2 will make batch API call)
        return [req["request_id"] for req in batch]

    def get_batch_info(self, batch_key: str) -> Dict[str, Any]:
        """Get info about a batch"""
        batch = self.batches.get(batch_key, [])
        return {
            "batch_key": batch_key,
            "size": len(batch),
            "created_at": self.batch_timers.get(batch_key),
            "requests": [req["request_id"] for req in batch]
        }

    def clear_expired_batches(self, timeout_seconds: int = None) -> int:
        """Clear expired batches - returns count removed"""
        timeout = timeout_seconds or (self.batch_timeout * 2)
        now = datetime.now()
        removed = 0

        keys_to_remove = []
        for batch_key, created_at in self.batch_timers.items():
            if (now - created_at).total_seconds() > timeout:
                keys_to_remove.append(batch_key)

        for batch_key in keys_to_remove:
            self.batches.pop(batch_key, None)
            self.batch_timers.pop(batch_key)
            removed += 1

        return removed


# Global instance
batch_manager = BatchManager()
