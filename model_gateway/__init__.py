"""
Model Gateway - Unified API for accessing multiple AI model providers.

Provides a centralized gateway for routing requests to different AI providers
(Anthropic, AWS Bedrock, etc.) with unified API, monitoring, and governance.
"""

__version__ = "1.0.0"

from .config import load_gateway_config, load_settings
from .providers import AnthropicProvider, BaseProvider, BedrockProvider

__all__ = [
    "BaseProvider",
    "AnthropicProvider",
    "BedrockProvider",
    "load_gateway_config",
    "load_settings",
]
