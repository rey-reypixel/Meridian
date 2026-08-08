import pytest
from app.services.cost_predictor import cost_predictor


class TestCostPredictor:
    """Test cost predictor service"""

    def test_count_tokens(self):
        """Test token counting"""
        text = "Hello world" * 10
        token_count = cost_predictor.count_tokens(text)
        assert token_count > 0
        assert isinstance(token_count, int)

    def test_estimate_cost(self):
        """Test cost estimation"""
        # Haiku: $0.80 per 1M input, $4 per 1M output
        cost = cost_predictor.estimate_cost("claude-haiku", 1_000_000, 1_000_000)
        expected = 0.80 + 4.0  # $4.80
        assert cost == expected

    def test_estimate_cost_opus(self):
        """Test Opus cost estimation"""
        # Opus: $15 per 1M input, $75 per 1M output
        cost = cost_predictor.estimate_cost("claude-opus", 1_000_000, 1_000_000)
        expected = 15.0 + 75.0  # $90.00
        assert cost == expected

    def test_estimate_cost_sonnet(self):
        """Test Sonnet cost estimation"""
        # Sonnet: $3 per 1M input, $15 per 1M output
        cost = cost_predictor.estimate_cost("claude-sonnet", 1_000_000, 1_000_000)
        expected = 3.0 + 15.0  # $18.00
        assert cost == expected

    def test_estimate_cost_zero_output(self):
        """Test cost with zero output tokens"""
        cost = cost_predictor.estimate_cost("claude-haiku", 1_000_000, 0)
        expected = 0.80
        assert cost == expected

    def test_estimate_from_text(self):
        """Test cost estimation from text"""
        text = "Hello world"
        result = cost_predictor.estimate_from_text(text, "claude-haiku")

        assert "estimated_cost" in result
        assert "token_count" in result
        assert result["model"] == "claude-haiku"
        assert result["estimated_cost"] > 0

    def test_unknown_model(self):
        """Test with unknown model"""
        with pytest.raises(ValueError):
            cost_predictor.estimate_cost("claude-unknown", 1000, 1000)

    def test_get_pricing(self):
        """Test getting pricing for models"""
        haiku_pricing = cost_predictor.get_pricing("claude-haiku")
        assert haiku_pricing["input_price"] == 0.80
        assert haiku_pricing["output_price"] == 4.0

        opus_pricing = cost_predictor.get_pricing("claude-opus")
        assert opus_pricing["input_price"] == 15.0
        assert opus_pricing["output_price"] == 75.0
