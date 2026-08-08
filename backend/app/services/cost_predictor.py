import tiktoken
from app.config import settings
from typing import Dict, Tuple


class CostPredictor:
    """Predict LLM API costs using tiktoken token counting"""

    # Claude model pricing ($ per 1M tokens)
    PRICING: Dict[str, Tuple[float, float]] = {
        "claude-opus": (
            settings.claude_opus_input_price,
            settings.claude_opus_output_price
        ),
        "claude-sonnet": (
            settings.claude_sonnet_input_price,
            settings.claude_sonnet_output_price
        ),
        "claude-haiku": (
            settings.claude_haiku_input_price,
            settings.claude_haiku_output_price
        ),
    }

    def __init__(self):
        """Initialize tiktoken encoder"""
        try:
            self.encoder = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            print(f"Warning: Could not load tiktoken encoder: {e}")
            self.encoder = None

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken"""
        if not text or not self.encoder:
            return 0
        return len(self.encoder.encode(text))

    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int = 0
    ) -> float:
        """
        Estimate cost for a request

        Args:
            model: Claude model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens (estimate if 0)

        Returns:
            Estimated cost in USD
        """
        if model not in self.PRICING:
            raise ValueError(f"Unknown model: {model}")

        input_price, output_price = self.PRICING[model]

        # Convert prices from per-million to per-token
        input_cost = (input_tokens / 1_000_000) * input_price
        output_cost = (output_tokens / 1_000_000) * output_price

        return round(input_cost + output_cost, 6)

    def estimate_from_text(
        self,
        text: str,
        model: str,
        expected_output_tokens: int = 512
    ) -> Dict[str, float | int]:
        """
        Estimate cost from raw text

        Args:
            text: Raw text to estimate
            model: Claude model name
            expected_output_tokens: Expected output tokens

        Returns:
            Dict with estimated_cost and token_count
        """
        token_count = self.count_tokens(text)
        cost = self.estimate_cost(model, token_count, expected_output_tokens)

        return {
            "estimated_cost": cost,
            "token_count": token_count,
            "input_tokens": token_count,
            "output_tokens": expected_output_tokens,
            "model": model
        }

    def get_pricing(self, model: str) -> Dict[str, float]:
        """Get pricing for a model"""
        if model not in self.PRICING:
            raise ValueError(f"Unknown model: {model}")

        input_price, output_price = self.PRICING[model]
        return {
            "input_price": input_price,
            "output_price": output_price,
            "currency": "USD",
            "unit": "per 1M tokens"
        }


# Global instance
cost_predictor = CostPredictor()
