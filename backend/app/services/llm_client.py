import anthropic
import asyncio
from typing import List, Dict, Any, AsyncGenerator
from app.config import settings
from app.services.cost_predictor import cost_predictor
import uuid


class OptimizedLLMClient:
    """Wrapper around Anthropic client for LLM requests"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        # Separate async client, needed for real streaming - the sync
        # client above can't do async iteration.
        self.async_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

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

    async def _mock_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Dev/test-only fake streaming - mirrors _mock_call but yields word-chunks"""
        input_text = "\n".join(m.get("content", "") for m in messages)
        content = f"[MOCK RESPONSE] Simulated {model} streaming completion for {len(messages)} message(s)."
        words = content.split(" ")

        for i, word in enumerate(words):
            chunk = word if i == 0 else f" {word}"
            yield {"type": "delta", "text": chunk}
            await asyncio.sleep(0.02)

        yield {
            "type": "done",
            "content": content,
            "input_tokens": cost_predictor.count_tokens(input_text),
            "output_tokens": min(cost_predictor.count_tokens(content), max_tokens),
        }

    async def stream_message(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system: str = "",
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream a completion. Yields {"type": "delta", "text": ...} chunks
        as they arrive, then a final {"type": "done", "content",
        "input_tokens", "output_tokens"}.
        """
        if settings.mock_anthropic:
            async for event in self._mock_stream(model, messages, max_tokens):
                yield event
            return

        try:
            async with self.async_client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system if system else None,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield {"type": "delta", "text": text}

                final_message = await stream.get_final_message()
                yield {
                    "type": "done",
                    "content": final_message.content[0].text,
                    "input_tokens": final_message.usage.input_tokens,
                    "output_tokens": final_message.usage.output_tokens,
                }
        except Exception as e:
            raise Exception(f"Error streaming from Claude API: {str(e)}")

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
