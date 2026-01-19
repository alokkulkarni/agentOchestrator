"""
Anthropic provider adapter for Model Gateway.

Handles communication with Anthropic's Claude API.
"""

import time
from typing import Any, Dict, List, Optional

import anthropic

from .base_provider import BaseProvider


class AnthropicProvider(BaseProvider):
    """Anthropic Claude API provider."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Anthropic provider.

        Args:
            config: Configuration dict with:
                - api_key: Anthropic API key
                - default_model: Default model to use
                - models: List of available models
        """
        super().__init__(config)
        self.api_key = config.get("api_key")
        if not self.api_key:
            raise ValueError("Anthropic API key is required")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.default_model = config.get(
            "default_model", "claude-sonnet-4-5-20250929"
        )

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a response using Anthropic's API.

        Args:
            messages: List of message dicts
            model: Model identifier (e.g., "claude-sonnet-4-5-20250929")
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            Standardized response dict
        """
        model = model or self.default_model

        # Convert messages to Anthropic format
        anthropic_messages = self._convert_messages(messages)

        try:
            # Call Anthropic API
            response = self.client.messages.create(
                model=model,
                messages=anthropic_messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            # Extract content
            content = ""
            if response.content:
                for block in response.content:
                    if block.type == "text":
                        content += block.text

            # Standardize response
            return self.standardize_response(
                content=content,
                model=response.model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                finish_reason=response.stop_reason or "stop",
            )

        except anthropic.APIError as e:
            raise Exception(f"Anthropic API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Error calling Anthropic: {str(e)}")

    async def health_check(self) -> Dict[str, Any]:
        """
        Check Anthropic API health.

        Returns:
            Health status dict
        """
        start_time = time.time()
        try:
            # Make a minimal API call to check health
            response = self.client.messages.create(
                model=self.default_model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=10,
            )

            latency_ms = (time.time() - start_time) * 1000

            return {
                "status": "healthy",
                "provider": "AnthropicProvider",
                "latency_ms": round(latency_ms, 2),
                "model": response.model,
                "error": None,
            }

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return {
                "status": "unhealthy",
                "provider": "AnthropicProvider",
                "latency_ms": round(latency_ms, 2),
                "error": str(e),
            }

    def _convert_messages(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert standard messages to Anthropic format.

        Args:
            messages: Standard message format

        Returns:
            Anthropic-formatted messages
        """
        anthropic_messages = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Anthropic uses "user" and "assistant" roles
            if role in ["user", "assistant"]:
                anthropic_messages.append({"role": role, "content": content})
            elif role == "system":
                # System messages are handled separately in Anthropic
                # For now, prepend to first user message
                if anthropic_messages and anthropic_messages[0]["role"] == "user":
                    anthropic_messages[0]["content"] = (
                        f"{content}\n\n{anthropic_messages[0]['content']}"
                    )
                else:
                    anthropic_messages.insert(
                        0, {"role": "user", "content": content}
                    )

        return anthropic_messages

    def get_model_info(self) -> Dict[str, Any]:
        """Get Anthropic model information."""
        return {
            "provider": "AnthropicProvider",
            "models": [
                "claude-sonnet-4-5-20250929",
                "claude-opus-4-5-20251101",
                "claude-3-5-sonnet-20241022",
                "claude-3-5-sonnet-20240620",
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
            ],
            "default_model": self.default_model,
        }
