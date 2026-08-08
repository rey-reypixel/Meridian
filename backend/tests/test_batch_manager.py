import pytest
import fakeredis
from unittest.mock import patch
from app.services.batch_manager import BatchManager


@pytest.fixture
def bm():
    """BatchManager backed by fakeredis instead of a live Redis server."""
    manager = BatchManager(batch_timeout_seconds=5, batch_size=3)
    manager.enabled = True
    manager.redis = fakeredis.FakeRedis(decode_responses=True)
    return manager


class TestBatchManager:
    def test_add_to_batch_returns_batch_key(self, bm):
        batch_key = bm.add_to_batch("req-1", "claude-haiku", "classification", {"foo": "bar"})
        assert batch_key == "claude-haiku:classification"

    def test_add_to_batch_disabled_returns_none(self, bm):
        bm.enabled = False
        result = bm.add_to_batch("req-1", "claude-haiku", "classification", {})
        assert result is None

    def test_batch_triggers_at_size_limit(self, bm):
        with patch("app.celery_app.process_batch_task") as mock_task:
            bm.add_to_batch("req-1", "claude-haiku", "classification", {})
            bm.add_to_batch("req-2", "claude-haiku", "classification", {})
            mock_task.delay.assert_not_called()

            bm.add_to_batch("req-3", "claude-haiku", "classification", {})
            mock_task.delay.assert_called_once_with("claude-haiku:classification")

    def test_pop_batch_returns_and_clears_items(self, bm):
        bm.add_to_batch("req-1", "claude-haiku", "summarization", {"x": 1})
        bm.add_to_batch("req-2", "claude-haiku", "summarization", {"x": 2})

        items = bm.pop_batch("claude-haiku:summarization")
        assert len(items) == 2
        assert {i["request_id"] for i in items} == {"req-1", "req-2"}

        assert bm.pop_batch("claude-haiku:summarization") == []

    def test_get_batch_info(self, bm):
        bm.add_to_batch("req-1", "claude-sonnet", "coding", {})
        info = bm.get_batch_info("claude-sonnet:coding")
        assert info["size"] == 1
        assert info["requests"] == ["req-1"]

    def test_wait_for_result_returns_immediately_when_ready(self, bm):
        bm.store_result("req-1", {"content": "hi"})
        result = bm.wait_for_result("req-1", "claude-haiku:general", timeout=1.0, poll_interval=0.05)
        assert result == {"content": "hi"}

    def test_wait_for_result_force_flushes_on_timeout(self, bm):
        bm.add_to_batch(
            "req-1", "claude-haiku", "general",
            {"model": "claude-haiku", "messages": [], "max_tokens": 10, "temperature": 0.7}
        )

        def fake_process(batch_key):
            for item in bm.pop_batch(batch_key):
                bm.store_result(item["request_id"], {"content": "forced"})

        with patch("app.celery_app.process_batch_task", side_effect=fake_process):
            result = bm.wait_for_result("req-1", "claude-haiku:general", timeout=0.3, poll_interval=0.05)

        assert result == {"content": "forced"}

    def test_wait_for_result_returns_none_if_never_resolved(self, bm):
        with patch("app.celery_app.process_batch_task"):
            result = bm.wait_for_result("nonexistent-req", "claude-haiku:general", timeout=0.2, poll_interval=0.05)
        assert result is None
