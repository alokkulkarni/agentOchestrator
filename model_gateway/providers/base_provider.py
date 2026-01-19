"""
Base provider interface for Model Gateway.

All provider adapters must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseProvider(ABC):
    """Abstract base class for AI model providers."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the provider.

        Args:
            config: Provider-specific configuration
        """
        self.config = config
        self.provider_name = self.__class__.__name__

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a response from the model.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier (provider-specific)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            **kwargs: Additional provider-specific parameters

        Returns:
            Standardized response dict with:
            {
                "content": str,
                "model": str,
                "usage": {
                    "input_tokens": int,
                    "output_tokens": int,
                    "total_tokens": int
                },
                "provider": str,
                "finish_reason": str
            }
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check if the provider is healthy and accessible.

        Returns:
            Dict with health status:
            {
                "status": "healthy" | "unhealthy",
                "provider": str,
                "latency_ms": float,
                "error": Optional[str]
            }
        """
        pass

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about available models.

        Returns:
            Dict with model information
        """
        return {
            "provider": self.provider_name,
            "models": self.config.get("models", []),
            "default_model": self.config.get("default_model"),
        }

    def standardize_response(
        self,
        content: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        finish_reason: str = "stop",
    ) -> Dict[str, Any]:
        """
        Convert provider-specific response to standardized format.

        Args:
            content: Generated text content
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            finish_reason: Reason for completion

        Returns:
            Standardized response dict
        """
        return {
            "content": content,
            "model": model,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
            "provider": self.provider_name,
            "finish_reason": finish_reason,
        }
