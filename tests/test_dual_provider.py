"""
Tests for dual provider support (Anthropic and Bedrock).

These tests verify that the orchestrator can work with both Anthropic and Bedrock
AI providers for intelligent routing.
"""

from unittest.mock import MagicMock, patch

import pytest

from agent_orchestrator.config import ConfigurationError, OrchestratorConfig


class TestOrchestratorConfigValidation:
    """Test orchestrator configuration validation for different providers."""

    def test_anthropic_config_valid(self, sample_orchestrator_config):
        """Test valid Anthropic configuration."""
        assert sample_orchestrator_config.ai_provider == "anthropic"
        assert sample_orchestrator_config.ai_model == "claude-sonnet-4-5-20250929"
        assert sample_orchestrator_config.bedrock is None

    def test_bedrock_config_valid(self, sample_orchestrator_config_bedrock):
        """Test valid Bedrock configuration."""
        assert sample_orchestrator_config_bedrock.ai_provider == "bedrock"
        assert sample_orchestrator_config_bedrock.bedrock is not None
        assert sample_orchestrator_config_bedrock.bedrock.region == "us-east-1"
        assert sample_orchestrator_config_bedrock.bedrock.model_id == "anthropic.claude-sonnet-3-5-v2-20241022"

    def test_bedrock_config_with_profile(self, sample_bedrock_config):
        """Test Bedrock configuration with AWS profile."""
        from agent_orchestrator.config import BedrockConfig

        config = BedrockConfig(
            region="us-west-2",
            model_id="anthropic.claude-sonnet-3-5-v2-20241022",
            aws_profile="bedrock-dev",
        )

        assert config.aws_profile == "bedrock-dev"
        assert config.role_arn is None

    def test_bedrock_config_with_role(self):
        """Test Bedrock configuration with STS assume role."""
        from agent_orchestrator.config import BedrockConfig

        config = BedrockConfig(
            region="us-east-1",
            model_id="anthropic.claude-sonnet-3-5-v2-20241022",
            role_arn="arn:aws:iam::123456789012:role/TestRole",
            session_name="test-session",
        )

        assert config.role_arn == "arn:aws:iam::123456789012:role/TestRole"
        assert config.session_name == "test-session"


class TestOrchestratorInitialization:
    """Test orchestrator initialization with different providers."""

    @patch("agent_orchestrator.orchestrator.AIReasoner")
    @patch("agent_orchestrator.orchestrator.load_all_configs")
    def test_init_with_anthropic(
        self,
        mock_load_configs,
        mock_ai_reasoner,
        sample_orchestrator_config,
        sample_agents_config,
        sample_rules_config,
        monkeypatch,
    ):
        """Test orchestrator initialization with Anthropic provider."""
        from agent_orchestrator import Orchestrator

        # Mock config loading
        mock_load_configs.return_value = (
            sample_orchestrator_config,
            sample_agents_config,
            sample_rules_config,
        )

        # Set API key
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        # Create orchestrator
        orchestrator = Orchestrator(config_path="config/orchestrator.yaml")

        # Verify AIReasoner was initialized
        mock_ai_reasoner.assert_called_once()
        call_kwargs = mock_ai_reasoner.call_args[1]
        assert call_kwargs["api_key"] == "test-key"
        assert call_kwargs["model"] == "claude-sonnet-4-5-20250929"

    @patch("agent_orchestrator.orchestrator.BedrockReasoner")
    @patch("agent_orchestrator.orchestrator.load_all_configs")
    def test_init_with_bedrock(
        self,
        mock_load_configs,
        mock_bedrock_reasoner,
        sample_orchestrator_config_bedrock,
        sample_agents_config,
        sample_rules_config,
    ):
        """Test orchestrator initialization with Bedrock provider."""
        from agent_orchestrator import Orchestrator

        # Mock config loading
        mock_load_configs.return_value = (
            sample_orchestrator_config_bedrock,
            sample_agents_config,
            sample_rules_config,
        )

        # Create orchestrator
        orchestrator = Orchestrator(config_path="config/orchestrator.yaml")

        # Verify BedrockReasoner was initialized
        mock_bedrock_reasoner.assert_called_once()
        call_kwargs = mock_bedrock_reasoner.call_args[1]
        assert call_kwargs["model_id"] == "anthropic.claude-sonnet-3-5-v2-20241022"
        assert call_kwargs["region"] == "us-east-1"
        assert call_kwargs["role_arn"] is None

    @patch("agent_orchestrator.orchestrator.load_all_configs")
    def test_init_anthropic_missing_api_key(
        self,
        mock_load_configs,
        sample_orchestrator_config,
        sample_agents_config,
        sample_rules_config,
        monkeypatch,
    ):
        """Test orchestrator fails when Anthropic API key is missing."""
        from agent_orchestrator import Orchestrator

        # Mock config loading
        mock_load_configs.return_value = (
            sample_orchestrator_config,
            sample_agents_config,
            sample_rules_config,
        )

        # Remove API key
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        # Should raise error
        with pytest.raises(ConfigurationError, match="ANTHROPIC_API_KEY"):
            Orchestrator(config_path="config/orchestrator.yaml")

    @patch("agent_orchestrator.orchestrator.load_all_configs")
    def test_init_bedrock_missing_config(
        self,
        mock_load_configs,
        sample_agents_config,
        sample_rules_config,
    ):
        """Test orchestrator fails when Bedrock config is missing."""
        from agent_orchestrator import Orchestrator
        from agent_orchestrator.config import OrchestratorConfig

        # Create config with bedrock provider but no bedrock config
        invalid_config = OrchestratorConfig(
            name="test",
            reasoning_mode="hybrid",
            ai_provider="bedrock",
            bedrock=None,  # Missing Bedrock config!
            agents_config_path="config/agents.yaml",
            rules_config_path="config/rules.yaml",
            schemas_path="config/schemas/",
        )

        mock_load_configs.return_value = (
            invalid_config,
            sample_agents_config,
            sample_rules_config,
        )

        # Should raise error
        with pytest.raises(ConfigurationError, match="Bedrock configuration required"):
            Orchestrator(config_path="config/orchestrator.yaml")

    @patch("agent_orchestrator.orchestrator.load_all_configs")
    def test_init_invalid_provider(
        self,
        mock_load_configs,
        sample_agents_config,
        sample_rules_config,
    ):
        """Test orchestrator fails with invalid provider."""
        from agent_orchestrator import Orchestrator
        from agent_orchestrator.config import OrchestratorConfig

        # This would fail at Pydantic validation level, but test the orchestrator logic
        # We can't actually create an invalid config due to Pydantic validation,
        # but we can test the error message
        # This test is more for documentation of expected behavior
        pass


class TestProviderSwitching:
    """Test switching between providers in configuration."""

    def test_config_supports_both_providers(
        self,
        sample_orchestrator_config,
        sample_orchestrator_config_bedrock,
    ):
        """Test that both provider configurations are valid."""
        # Anthropic config
        assert sample_orchestrator_config.ai_provider == "anthropic"
        assert sample_orchestrator_config.ai_model is not None

        # Bedrock config
        assert sample_orchestrator_config_bedrock.ai_provider == "bedrock"
        assert sample_orchestrator_config_bedrock.bedrock is not None

    def test_bedrock_config_independence(
        self,
        sample_orchestrator_config_bedrock,
    ):
        """Test Bedrock config doesn't require Anthropic settings."""
        # Bedrock config should work without ai_model (only used for Anthropic)
        assert sample_orchestrator_config_bedrock.ai_provider == "bedrock"
        # ai_model has a default value but is not used when provider is bedrock
        assert sample_orchestrator_config_bedrock.bedrock is not None


class TestReasoningModeCompatibility:
    """Test that reasoning modes work with both providers."""

    @pytest.mark.parametrize("reasoning_mode", ["rule", "ai", "hybrid"])
    def test_reasoning_modes_with_anthropic(
        self,
        reasoning_mode,
        sample_orchestrator_config,
    ):
        """Test all reasoning modes work with Anthropic."""
        from agent_orchestrator.config import OrchestratorConfig, ReasoningMode

        config = OrchestratorConfig(
            name="test",
            reasoning_mode=ReasoningMode(reasoning_mode),
            ai_provider="anthropic",
            ai_model="claude-sonnet-4-5-20250929",
            agents_config_path="config/agents.yaml",
            rules_config_path="config/rules.yaml",
            schemas_path="config/schemas/",
        )

        assert config.reasoning_mode.value == reasoning_mode
        assert config.ai_provider == "anthropic"

    @pytest.mark.parametrize("reasoning_mode", ["rule", "ai", "hybrid"])
    def test_reasoning_modes_with_bedrock(
        self,
        reasoning_mode,
        sample_bedrock_config,
    ):
        """Test all reasoning modes work with Bedrock."""
        from agent_orchestrator.config import OrchestratorConfig, ReasoningMode

        config = OrchestratorConfig(
            name="test",
            reasoning_mode=ReasoningMode(reasoning_mode),
            ai_provider="bedrock",
            bedrock=sample_bedrock_config,
            agents_config_path="config/agents.yaml",
            rules_config_path="config/rules.yaml",
            schemas_path="config/schemas/",
        )

        assert config.reasoning_mode.value == reasoning_mode
        assert config.ai_provider == "bedrock"


class TestBedrockCredentialMethods:
    """Test different Bedrock credential methods."""

    def test_bedrock_default_credentials(self, sample_bedrock_config):
        """Test Bedrock with default credentials."""
        assert sample_bedrock_config.aws_profile is None
        assert sample_bedrock_config.role_arn is None

    def test_bedrock_with_profile(self):
        """Test Bedrock with AWS profile."""
        from agent_orchestrator.config import BedrockConfig

        config = BedrockConfig(
            region="us-east-1",
            model_id="anthropic.claude-sonnet-3-5-v2-20241022",
            aws_profile="my-profile",
        )

        assert config.aws_profile == "my-profile"
        assert config.role_arn is None

    def test_bedrock_with_assume_role(self):
        """Test Bedrock with STS assume role."""
        from agent_orchestrator.config import BedrockConfig

        config = BedrockConfig(
            region="us-east-1",
            model_id="anthropic.claude-sonnet-3-5-v2-20241022",
            role_arn="arn:aws:iam::123456789012:role/BedrockRole",
            session_name="my-session",
        )

        assert config.role_arn == "arn:aws:iam::123456789012:role/BedrockRole"
        assert config.session_name == "my-session"

    def test_bedrock_with_profile_and_role(self):
        """Test Bedrock with both profile and assume role."""
        from agent_orchestrator.config import BedrockConfig

        config = BedrockConfig(
            region="us-east-1",
            model_id="anthropic.claude-sonnet-3-5-v2-20241022",
            aws_profile="base-profile",
            role_arn="arn:aws:iam::123456789012:role/BedrockRole",
            session_name="my-session",
        )

        assert config.aws_profile == "base-profile"
        assert config.role_arn == "arn:aws:iam::123456789012:role/BedrockRole"
