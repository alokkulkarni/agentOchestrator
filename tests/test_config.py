"""Tests for configuration loading and validation."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from agent_orchestrator.config import (
    AgentConfig,
    AgentType,
    ConfigurationError,
    load_agents_config,
    load_orchestrator_config,
    load_yaml_file,
    OrchestratorConfig,
)


class TestConfigLoader:
    """Test configuration loading."""

    def test_load_yaml_file(self, tmp_path):
        """Test YAML file loading."""
        config_file = tmp_path / "test.yaml"

        config_data = {
            "name": "test",
            "value": 42,
        }

        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        loaded = load_yaml_file(config_file)

        assert loaded["name"] == "test"
        assert loaded["value"] == 42

    def test_load_yaml_with_env_vars(self, tmp_path, monkeypatch):
        """Test environment variable substitution."""
        config_file = tmp_path / "test.yaml"

        config_data = {
            "api_key": "${TEST_API_KEY}",
            "url": "${TEST_URL:http://default}",
        }

        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        monkeypatch.setenv("TEST_API_KEY", "secret-key")

        loaded = load_yaml_file(config_file)

        assert loaded["api_key"] == "secret-key"
        assert loaded["url"] == "http://default"  # Uses default

    def test_load_yaml_file_not_found(self):
        """Test loading non-existent file."""
        with pytest.raises(ConfigurationError):
            load_yaml_file("nonexistent.yaml")


class TestOrchestratorConfig:
    """Test orchestrator configuration."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = OrchestratorConfig()

        assert config.name == "agent-orchestrator"
        assert config.reasoning_mode == "hybrid"
        assert config.max_parallel_agents == 3
        assert config.default_timeout == 30

    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        config = OrchestratorConfig(
            name="test",
            max_parallel_agents=5,
        )

        assert config.max_parallel_agents == 5

        # Invalid config (exceeds max)
        with pytest.raises(Exception):  # Pydantic ValidationError
            OrchestratorConfig(max_parallel_agents=100)


class TestAgentConfig:
    """Test agent configuration."""

    def test_mcp_agent_config(self):
        """Test MCP agent configuration."""
        from agent_orchestrator.config import MCPConnectionConfig

        config = AgentConfig(
            name="test-mcp",
            type=AgentType.MCP,
            connection=MCPConnectionConfig(
                url="http://localhost:8080",
                timeout=30,
            ),
            capabilities=["test"],
        )

        assert config.type == AgentType.MCP
        assert config.connection.url == "http://localhost:8080"

    def test_direct_agent_config(self):
        """Test direct agent configuration."""
        from agent_orchestrator.config import DirectToolConfig

        config = AgentConfig(
            name="test-direct",
            type=AgentType.DIRECT,
            direct_tool=DirectToolConfig(
                module="examples.sample_calculator",
                function="calculate",
            ),
            capabilities=["math"],
        )

        assert config.type == AgentType.DIRECT
        assert config.direct_tool.module == "examples.sample_calculator"

    def test_agent_config_validation(self):
        """Test agent configuration validation."""
        from pydantic import ValidationError

        # MCP agent missing connection config
        with pytest.raises(ValidationError):
            AgentConfig(
                name="test",
                type=AgentType.MCP,
                capabilities=["test"],
            )

        # Direct agent missing tool config
        with pytest.raises(ValidationError):
            AgentConfig(
                name="test",
                type=AgentType.DIRECT,
                capabilities=["test"],
            )
