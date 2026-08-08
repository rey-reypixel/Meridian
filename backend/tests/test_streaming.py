import json
import pytest
from unittest.mock import patch
from tests.conftest import TestingSessionLocal
from app.services.response_cache import response_cache


def fake_similarity(text_a: str, text_b: str) -> float:
    """Deterministic stand-in for embedding cosine similarity (see
    tests/test_model_router.py) - avoids needing live Redis/FastEmbed for
    the task classification step inside _prepare_optimized_request."""
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a or not words_b:
        return 0.0
    overlap = words_a & words_b
    return len(overlap) / max(len(words_a), len(words_b))


@pytest.fixture(autouse=True)
def mock_embeddings():
    # Caching behavior itself is covered by tests/test_response_cache.py -
    # here it just needs to be off so response_cache.get()/.set() don't
    # try to hit a real (unreachable in this test run) Redis.
    original_cache_enabled = response_cache.enabled
    response_cache.enabled = False
    with patch("app.services.model_router.embedding_service.similarity", side_effect=fake_similarity):
        yield
    response_cache.enabled = original_cache_enabled


async def fake_stream_message(model, messages, max_tokens, temperature, system=""):
    yield {"type": "delta", "text": "Hello"}
    yield {"type": "delta", "text": " world"}
    yield {"type": "done", "content": "Hello world", "input_tokens": 5, "output_tokens": 3}


def parse_sse_events(text):
    """Extract the JSON payload from each `data: ...` SSE line"""
    events = []
    for line in text.split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: "):]))
    return events


@pytest.fixture(autouse=True)
def patch_stream_db_session():
    """
    The streaming endpoint deliberately opens its own SessionLocal() rather
    than using Depends(get_db) - see the comment in routes.py - so the
    conftest `client` fixture's get_db override doesn't reach it. Redirect
    the SessionLocal reference routes.py actually uses to the same test
    sessionmaker (bound to the same SQLite test engine as the `db` fixture),
    so writes made during the stream are visible to `db` afterward.
    """
    with patch("app.api.routes.SessionLocal", TestingSessionLocal):
        yield


class TestStreaming:
    def test_stream_requires_auth(self, client):
        response = client.post("/api/messages/stream", json={
            "model": "claude-opus",
            "messages": [{"role": "user", "content": "Hello"}]
        })
        assert response.status_code == 401

    def test_stream_rejects_batch(self, authenticated_client):
        response = authenticated_client.post("/api/messages/stream", json={
            "model": "claude-opus",
            "messages": [{"role": "user", "content": "Hello"}],
            "batch": True
        })
        assert response.status_code == 400

    @patch("app.services.llm_client.llm_client.stream_message", side_effect=fake_stream_message)
    def test_stream_delivers_chunks_in_order_then_done(self, mock_stream, authenticated_client):
        # optimize_for=quality keeps model_used deterministic (no downgrade)
        # so this test can focus on verifying chunk order + final metadata
        # shape, not on routing behavior (covered in test_model_router.py).
        response = authenticated_client.post("/api/messages/stream", json={
            "model": "claude-opus",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 50,
            "optimize_for": "quality"
        })
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        events = parse_sse_events(response.text)
        assert events[0] == {"text": "Hello"}
        assert events[1] == {"text": " world"}

        final = events[-1]
        assert final["done"] is True
        assert final["metadata"]["model_used"] == "claude-opus"
        assert "request_id" in final["metadata"]
        assert final["metadata"]["cost"] > 0

    @patch("app.services.llm_client.llm_client.stream_message", side_effect=fake_stream_message)
    def test_stream_persists_request_to_db(self, mock_stream, authenticated_client, db):
        from app.db.models import ApiRequest

        response = authenticated_client.post("/api/messages/stream", json={
            "model": "claude-haiku",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 50
        })
        events = parse_sse_events(response.text)
        request_id = events[-1]["metadata"]["request_id"]

        saved = db.query(ApiRequest).filter(ApiRequest.id == request_id).first()
        assert saved is not None
        assert saved.input_tokens == 5
        assert saved.output_tokens == 3
