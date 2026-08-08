import anthropic
from typing import List, Dict, Any
from app.config import settings
from app.services.cost_predictor import cost_predictor
import uuid


class OptimizedLLMClient:
    """Wrapper around Anthropic client for LLM requests"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def _mock_call(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
    ) -> Dict[str, Any]:
        """Dev/test-only fake completion - see settings.mock_anthropic"""
        input_text = "\n".join(m.get("content", "") for m in messages)
        content = f"[MOCK RESPONSE] Simulated {model} completion for {len(messages)} message(s)."
        return {
            "content": content,
            "stop_reason": "end_turn",
            "input_tokens": cost_predictor.count_tokens(input_text),
            "output_tokens": min(cost_predictor.count_tokens(content), max_tokens),
            "request_id": str(uuid.uuid4())
        }

    def _call(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        system: str,
    ) -> Dict[str, Any]:
        if settings.mock_anthropic:
            return self._mock_call(model, messages, max_tokens)

        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system if system else None,
                messages=messages
            )

            return {
                "content": response.content[0].text,
                "stop_reason": response.stop_reason,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "request_id": str(uuid.uuid4())
            }
        except Exception as e:
            raise Exception(f"Error calling Claude API: {str(e)}")

    async def create_message(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system: str = "",
    ) -> Dict[str, Any]:
        """
        Create a message using Claude API

        Args:
            model: Model name (claude-opus, claude-sonnet, claude-haiku)
            messages: List of message dicts with role and content
            max_tokens: Max tokens in response
            temperature: Sampling temperature
            system: System prompt

        Returns:
            Response with content and usage info
        """
        return self._call(model, messages, max_tokens, temperature, system)

    def create_message_sync(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system: str = "",
    ) -> Dict[str, Any]:
        """
        Synchronous variant of create_message, for use inside Celery tasks
        (the worker process has no event loop to await into).
        """
        return self._call(model, messages, max_tokens, temperature, system)

    async def count_tokens_for_messages(
        self,
        model: str,
        messages: List[Dict[str, str]],
        system: str = "",
    ) -> int:
        """
        Count tokens for a message using Claude's tokenizer

        Note: This is an approximation. Actual token count may differ.
        """
        # Simple token counting: rough estimation
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        if system:
            total_chars += len(system)

        # Rough estimate: ~4 chars per token
        return int(total_chars / 4)


# Global instance
llm_client = OptimizedLLMClient()
