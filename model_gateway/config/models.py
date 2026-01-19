"""
Configuration models for Model Gateway using Pydantic.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderConfig(BaseModel):
    """Configuration for a single provider."""

    type: str = Field(..., description="Provider type (anthropic, bedrock)")
    enabled: bool = Field(default=True, description="Whether provider is enabled")
    default_model: Optional[str] = Field(
        default=None, description="Default model for this provider"
    )

    # Anthropic-specific
    api_key: Optional[str] = Field(default=None, description="Anthropic API key")

    # Bedrock-specific
    region: Optional[str] = Field(default=None, description="AWS region")
    model_id: Optional[str] = Field(default=None, description="Bedrock model ID")
    aws_profile: Optional[str] = Field(
        default=None, description="AWS profile name"
    )
    role_arn: Optional[str] = Field(default=None, description="IAM role ARN")
    session_name: Optional[str] = Field(
        default=None, description="STS session name"
    )

    # Common
    timeout: int = Field(default=60, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""

    enabled: bool = Field(default=False, description="Enable rate limiting")
    requests_per_minute: int = Field(
        default=60, description="Max requests per minute"
    )
    tokens_per_minute: int = Field(
        default=100000, description="Max tokens per minute"
    )


class GatewaySettings(BaseSettings):
    """Main gateway configuration from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="GATEWAY_",
        env_file=["model_gateway/.env", ".env"],  # Check both locations
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8585, description="Server port")
    reload: bool = Field(default=False, description="Auto-reload on code changes")

    # Authentication
    api_key: Optional[str] = Field(
        default=None, description="Gateway API key for authentication"
    )
    require_auth: bool = Field(
        default=False, description="Require authentication"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_requests: bool = Field(default=True, description="Log all requests")

    # Provider settings (from environment)
    anthropic_api_key: Optional[str] = Field(
        default=None, description="Anthropic API key"
    )
    aws_region: Optional[str] = Field(default="us-east-1", description="AWS region")
    aws_profile: Optional[str] = Field(
        default=None, description="AWS profile name"
    )


class FallbackConfig(BaseModel):
    """Provider fallback configuration."""

    enabled: bool = Field(
        default=True, description="Enable automatic provider fallback"
    )
    fallback_order: List[str] = Field(
        default_factory=lambda: ["anthropic", "bedrock"],
        description="Order of providers to try on failure"
    )
    retry_original: bool = Field(
        default=False,
        description="Retry original provider after fallback"
    )
    max_fallback_attempts: int = Field(
        default=2,
        description="Maximum number of fallback attempts"
    )


class GatewayConfig(BaseModel):
    """Complete gateway configuration."""

    providers: Dict[str, ProviderConfig] = Field(
        default_factory=dict, description="Provider configurations"
    )
    rate_limit: RateLimitConfig = Field(
        default_factory=RateLimitConfig, description="Rate limiting config"
    )
    default_provider: str = Field(
        default="anthropic", description="Default provider to use"
    )
    fallback: FallbackConfig = Field(
        default_factory=FallbackConfig, description="Provider fallback configuration"
    )
