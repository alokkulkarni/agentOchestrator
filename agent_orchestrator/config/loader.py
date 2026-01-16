"""
Configuration loader for YAML-based configuration files.

This module provides functions to load and validate configuration files
using Pydantic models for type safety and validation.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, TypeVar

import yaml
from pydantic import ValidationError

from .models import AgentsFileConfig, OrchestratorConfig, RulesFileConfig

T = TypeVar("T")


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""
    pass


def _substitute_env_vars(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively substitute environment variables in configuration.

    Supports syntax: ${ENV_VAR} or ${ENV_VAR:default_value}

    Args:
        config_dict: Configuration dictionary

    Returns:
        Dictionary with environment variables substituted
    """
    env_pattern = re.compile(r'\$\{([^}:]+)(?::([^}]*))?\}')

    def substitute_value(value: Any) -> Any:
        """Recursively substitute environment variables."""
        if isinstance(value, str):
            def replace_match(match: re.Match[str]) -> str:
                env_var = match.group(1)
                default = match.group(2) if match.group(2) is not None else ""
                return os.environ.get(env_var, default)

            return env_pattern.sub(replace_match, value)
        elif isinstance(value, dict):
            return {k: substitute_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [substitute_value(item) for item in value]
        else:
            return value

    return substitute_value(config_dict)


def load_yaml_file(file_path: str | Path) -> Dict[str, Any]:
    """
    Load and parse a YAML file with environment variable substitution.

    Args:
        file_path: Path to YAML file

    Returns:
        Parsed configuration dictionary

    Raises:
        ConfigurationError: If file cannot be loaded or parsed
    """
    path = Path(file_path)

    if not path.exists():
        raise ConfigurationError(f"Configuration file not found: {file_path}")

    if not path.is_file():
        raise ConfigurationError(f"Configuration path is not a file: {file_path}")

    try:
        with open(path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Failed to parse YAML file {file_path}: {e}")
    except Exception as e:
        raise ConfigurationError(f"Failed to read file {file_path}: {e}")

    if not isinstance(config_dict, dict):
        raise ConfigurationError(f"Configuration file must contain a dictionary: {file_path}")

    # Substitute environment variables
    config_dict = _substitute_env_vars(config_dict)

    return config_dict


def validate_config(config_dict: Dict[str, Any], model_class: type[T]) -> T:
    """
    Validate configuration dictionary against a Pydantic model.

    Args:
        config_dict: Configuration dictionary
        model_class: Pydantic model class to validate against

    Returns:
        Validated model instance

    Raises:
        ConfigurationError: If validation fails
    """
    try:
        return model_class(**config_dict)
    except ValidationError as e:
        error_messages = []
        for error in e.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            msg = error["msg"]
            error_messages.append(f"  {field}: {msg}")

        raise ConfigurationError(
            f"Configuration validation failed for {model_class.__name__}:\n" +
            "\n".join(error_messages)
        )


def load_orchestrator_config(file_path: str | Path = "config/orchestrator.yaml") -> OrchestratorConfig:
    """
    Load and validate main orchestrator configuration.

    Args:
        file_path: Path to orchestrator configuration file

    Returns:
        Validated orchestrator configuration

    Raises:
        ConfigurationError: If loading or validation fails
    """
    config_dict = load_yaml_file(file_path)
    return validate_config(config_dict, OrchestratorConfig)


def load_agents_config(file_path: str | Path = "config/agents.yaml") -> AgentsFileConfig:
    """
    Load and validate agents configuration.

    Args:
        file_path: Path to agents configuration file

    Returns:
        Validated agents configuration

    Raises:
        ConfigurationError: If loading or validation fails
    """
    config_dict = load_yaml_file(file_path)
    return validate_config(config_dict, AgentsFileConfig)


def load_rules_config(file_path: str | Path = "config/rules.yaml") -> RulesFileConfig:
    """
    Load and validate routing rules configuration.

    Args:
        file_path: Path to rules configuration file

    Returns:
        Validated rules configuration

    Raises:
        ConfigurationError: If loading or validation fails
    """
    config_dict = load_yaml_file(file_path)
    return validate_config(config_dict, RulesFileConfig)


def load_all_configs(
    orchestrator_path: str | Path = "config/orchestrator.yaml"
) -> tuple[OrchestratorConfig, AgentsFileConfig, RulesFileConfig]:
    """
    Load all configuration files.

    Args:
        orchestrator_path: Path to orchestrator config (contains paths to other configs)

    Returns:
        Tuple of (orchestrator_config, agents_config, rules_config)

    Raises:
        ConfigurationError: If any configuration fails to load or validate
    """
    # Load main orchestrator config
    orch_config = load_orchestrator_config(orchestrator_path)

    # Get paths to other config files (relative to orchestrator config location)
    base_path = Path(orchestrator_path).parent
    agents_path = base_path / orch_config.agents_config_path
    rules_path = base_path / orch_config.rules_config_path

    # Load agents and rules configs
    agents_config = load_agents_config(agents_path)
    rules_config = load_rules_config(rules_path)

    return orch_config, agents_config, rules_config
