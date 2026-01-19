"""
Configuration loader for Model Gateway.

Loads configuration from YAML files and environment variables.
"""

import os
from pathlib import Path
from typing import Dict, Any

import yaml

from .models import GatewayConfig, GatewaySettings, ProviderConfig


def load_gateway_config(config_path: str = None) -> GatewayConfig:
    """
    Load gateway configuration from file and environment.

    Args:
        config_path: Path to gateway config YAML file

    Returns:
        GatewayConfig object
    """
    # Default config path
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "config",
            "gateway.yaml",
        )

    # Load from YAML if file exists
    gateway_config_dict = {}
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            gateway_config_dict = yaml.safe_load(f) or {}

    # Load environment settings
    settings = GatewaySettings()

    # Merge environment variables into provider configs
    providers = gateway_config_dict.get("providers", {})

    # Update Anthropic provider with env var if available
    if "anthropic" in providers and settings.anthropic_api_key:
        providers["anthropic"]["api_key"] = settings.anthropic_api_key

    # Update Bedrock provider with env vars if available
    if "bedrock" in providers:
        if settings.aws_region:
            providers["bedrock"]["region"] = settings.aws_region
        if settings.aws_profile:
            providers["bedrock"]["aws_profile"] = settings.aws_profile

    # Convert provider dicts to ProviderConfig objects
    provider_configs = {}
    for name, config in providers.items():
        provider_configs[name] = ProviderConfig(**config)

    gateway_config_dict["providers"] = provider_configs

    # Create GatewayConfig
    return GatewayConfig(**gateway_config_dict)


def load_settings() -> GatewaySettings:
    """
    Load gateway settings from environment variables.

    Returns:
        GatewaySettings object
    """
    return GatewaySettings()
