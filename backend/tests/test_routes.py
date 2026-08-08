import pytest
from unittest.mock import patch, MagicMock
from app.db.models import User


class TestAuthRoutes:
    """Test authentication routes"""

    def test_login_endpoint(self, client):
        """Test login endpoint returns Google OAuth URL"""
        response = client.get("/auth/login")
        assert response.status_code == 200
        data = response.json()
        assert "auth_url" in data
        assert "accounts.google.com" in data["auth_url"]

    def test_logout_endpoint(self, authenticated_client):
        """Test logout endpoint"""
        response = authenticated_client.post("/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestMessagesRoutes:
    """Test message creation routes"""

    @patch("app.services.llm_client.llm_client.create_message")
    def test_create_message_requires_auth(self, mock_llm, client):
        """Test that messages endpoint requires authentication"""
        response = client.post("/api/messages", json={
            "model": "claude-opus",
            "messages": [{"role": "user", "content": "Hello"}]
        })
        assert response.status_code == 401

    @patch("app.services.llm_client.llm_client.create_message")
    def test_create_message_authenticated(self, mock_llm, authenticated_client):
        """Test creating a message with authentication"""
        mock_llm.return_value = {
            "content": "Hello! How can I help?",
            "stop_reason": "end_turn",
            "input_tokens": 10,
            "output_tokens": 5,
            "request_id": "test-123"
        }

        response = authenticated_client.post("/api/messages", json={
            "model": "claude-opus",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 1024,
            "temperature": 0.7,
            "optimize_for": "cost"
        })

        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "metadata" in data
        assert data["content"]["content"] == "Hello! How can I help?"
        assert data["metadata"]["cost"] > 0

    @patch("app.services.llm_client.llm_client.create_message")
    def test_create_message_cost_limit_rejects_when_exceeded(self, mock_llm, authenticated_client):
        """cost_limit should block the request before any LLM call happens"""
        response = authenticated_client.post("/api/messages", json={
            "model": "claude-opus",
            "messages": [{"role": "user", "content": "Hello " * 500}],
            "max_tokens": 1024,
            "cost_limit": 0.0000001
        })
        assert response.status_code == 402
        assert "cost_limit" in response.json()["detail"]
        mock_llm.assert_not_called()

    @patch("app.services.llm_client.llm_client.create_message")
    def test_create_message_optimize_for_quality_skips_routing(self, mock_llm, authenticated_client):
        """optimize_for=quality should never downgrade below the requested model"""
        mock_llm.return_value = {
            "content": "classified",
            "stop_reason": "end_turn",
            "input_tokens": 10,
            "output_tokens": 5,
            "request_id": "test-quality"
        }
        response = authenticated_client.post("/api/messages", json={
            "model": "claude-opus",
            "messages": [{"role": "user", "content": "Classify this email as spam"}],
            "optimize_for": "quality"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["model_used"] == "claude-opus"
        assert "model_routing" not in data["metadata"]["optimizations_applied"]

    @patch("app.services.llm_client.llm_client.create_message")
    def test_create_message_optimize_for_speed_skips_truncation(self, mock_llm, authenticated_client):
        """optimize_for=speed should skip context truncation (no embedding latency)"""
        mock_llm.return_value = {
            "content": "ok",
            "stop_reason": "end_turn",
            "input_tokens": 10,
            "output_tokens": 5,
            "request_id": "test-speed"
        }
        many_messages = [{"role": "user", "content": f"message {i}"} for i in range(10)]
        response = authenticated_client.post("/api/messages", json={
            "model": "claude-haiku",
            "messages": many_messages,
            "optimize_for": "speed"
        })
        assert response.status_code == 200
        data = response.json()
        assert "context_truncation" not in data["metadata"]["optimizations_applied"]
        sent_messages = mock_llm.call_args.kwargs["messages"]
        assert len(sent_messages) == len(many_messages)

    def test_create_message_invalid_optimize_for_rejected(self, authenticated_client):
        """optimize_for must be one of cost/speed/quality - typos should 422, not silently fall through"""
        response = authenticated_client.post("/api/messages", json={
            "model": "claude-opus",
            "messages": [{"role": "user", "content": "Hello"}],
            "optimize_for": "qualtiy"
        })
        assert response.status_code == 422

    def test_estimate_cost_requires_auth(self, client):
        """Test that cost estimation requires authentication"""
        response = client.get("/api/estimate?prompt=test&model=claude-opus")
        assert response.status_code == 401

    def test_estimate_cost_authenticated(self, authenticated_client):
        """Test cost estimation with authentication"""
        response = authenticated_client.get("/api/estimate?prompt=Hello+world&model=claude-haiku")
        assert response.status_code == 200
        data = response.json()
        assert "estimated_cost" in data
        assert "token_count" in data
        assert data["model"] == "claude-haiku"

    def test_estimate_cost_invalid_model(self, authenticated_client):
        """Test cost estimation with invalid model"""
        response = authenticated_client.get("/api/estimate?prompt=test&model=invalid-model")
        assert response.status_code == 400


class TestDashboardRoutes:
    """Test dashboard routes"""

    def test_dashboard_summary_requires_auth(self, client):
        """Test that dashboard summary requires authentication"""
        response = client.get("/api/dashboard/summary")
        assert response.status_code == 401

    def test_dashboard_summary_authenticated(self, authenticated_client):
        """Test dashboard summary with authentication"""
        response = authenticated_client.get("/api/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_spend_month" in data
        assert "optimized_spend_month" in data
        assert "total_savings" in data
        assert "savings_percentage" in data
        assert "requests_optimized" in data

    def test_dashboard_models_requires_auth(self, client):
        """Test that dashboard models requires authentication"""
        response = client.get("/api/dashboard/models")
        assert response.status_code == 401

    def test_dashboard_models_authenticated(self, authenticated_client):
        """Test dashboard models breakdown with authentication"""
        response = authenticated_client.get("/api/dashboard/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert isinstance(data["models"], list)


class TestHealthCheck:
    """Test health check endpoints"""

    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "Meridian"

    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Meridian"
        assert data["version"] == "0.1.0"
