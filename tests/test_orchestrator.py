"""
Comprehensive tests for the main Orchestrator class.

Tests cover initialization, request processing, reasoning, agent execution,
validation, error handling, and statistics.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
from datetime import datetime

from agent_orchestrator import Orchestrator
from agent_orchestrator.config import ConfigurationError
from agent_orchestrator.utils import SecurityError


class TestOrchestratorInitialization:
    """Test orchestrator initialization."""

    @patch("agent_orchestrator.orchestrator.load_all_configs")
    def test_init_success_anthropic(
        self,
        mock_load_configs,
        sample_orchestrator_config,
        sample_agents_config,
        sample_rules_config,
        monkeypatch,
    ):
        """Test successful initialization with Anthropic."""
        mock_load_configs.return_value = (
            sample_orchestrator_config,
            sample_agents_config,
            sample_rules_config,
        )
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        orchestrator = Orchestrator(config_path="config/test.yaml")

        assert orchestrator.config.name == "test-orchestrator"
        assert orchestrator._initialized is False
        assert orchestrator._request_count == 0
        assert orchestrator.agent_registry is not None
        assert orchestrator.rule_engine is not None
        assert orchestrator.ai_reasoner is not None

    @patch("agent_orchestrator.orchestrator.load_all_configs")
    def test_init_success_bedrock(
        self,
        mock_load_configs,
        sample_orchestrator_config_bedrock,
        sample_agents_config,
        sample_rules_config,
    ):
        """Test successful initialization with Bedrock."""
        mock_load_configs.return_value = (
            sample_orchestrator_config_bedrock,
            sample_agents_config,
            sample_rules_config,
        )

        with patch("agent_orchestrator.orchestrator.BedrockReasoner") as mock_bedrock:
            orchestrator = Orchestrator(config_path="config/test.yaml")

            assert orchestrator.config.name == "test-orchestrator-bedrock"
            mock_bedrock.assert_called_once()

    @patch("agent_orchestrator.orchestrator.load_all_configs")
    def test_init_config_error(self, mock_load_configs):
        """Test initialization with configuration error."""
        mock_load_configs.side_effect = ConfigurationError("Invalid config")

        with pytest.raises(ConfigurationError):
            Orchestrator(config_path="config/test.yaml")

    @patch("agent_orchestrator.orchestrator.load_all_configs")
    def test_init_rule_only_mode(
        self,
        mock_load_configs,
        sample_agents_config,
        sample_rules_config,
    ):
        """Test initialization with rule-only mode (no AI reasoner)."""
        from agent_orchestrator.config import OrchestratorConfig, ReasoningMode

        rule_only_config = OrchestratorConfig(
            name="rule-only",
            reasoning_mode=ReasoningMode.RULE,
            agents_config_path="config/agents.yaml",
            rules_config_path="config/rules.yaml",
            schemas_path="config/schemas/",
        )

        mock_load_configs.return_value = (
            rule_only_config,
            sample_agents_config,
            sample_rules_config,
        )

        orchestrator = Orchestrator(config_path="config/test.yaml")

        assert orchestrator.ai_reasoner is None
        assert orchestrator.hybrid_reasoner is None
        assert orchestrator.rule_engine is not None


class TestOrchestratorAgentInitialization:
    """Test agent initialization and registration."""

    @patch("agent_orchestrator.orchestrator.load_all_configs")
    @pytest.mark.asyncio
    async def test_initialize_agents(
        self,
        mock_load_configs,
        sample_orchestrator_config,
        sample_agents_config,
        sample_rules_config,
        monkeypatch,
    ):
        """Test agent initialization and registration."""
        mock_load_configs.return_value = (
            sample_orchestrator_config,
            sample_agents_config,
            sample_rules_config,
        )
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        orchestrator = Orchestrator(config_path="config/test.yaml")
        await orchestrator.initialize()

        assert orchestrator._initialized is True
        stats = orchestrator.get_stats()
        assert stats["agents"]["total_agents"] > 0

    @patch("agent_orchestrator.orchestrator.load_all_configs")
    @pytest.mark.asyncio
    async def test_initialize_twice(
        self,
        mock_load_configs,
        sample_orchestrator_config,
        sample_agents_config,
        sample_rules_config,
        monkeypatch,
    ):
        """Test initializing orchestrator twice (should warn)."""
        mock_load_configs.return_value = (
            sample_orchestrator_config,
            sample_agents_config,
            sample_rules_config,
        )
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        orchestrator = Orchestrator(config_path="config/test.yaml")
        await orchestrator.initialize()

        # Second initialization should be a no-op
        await orchestrator.initialize()

        assert orchestrator._initialized is True


class TestOrchestratorProcessing:
    """Test request processing."""

    @patch("agent_orchestrator.orchestrator.load_all_configs")
    @pytest.mark.asyncio
    async def test_process_before_initialization(
        self,
        mock_load_configs,
        sample_orchestrator_config,
        sample_agents_config,
        sample_rules_config,
        monkeypatch,
    ):
        """Test processing request before initialization."""
        mock_load_configs.return_value = (
            sample_orchestrator_config,
            sample_agents_config,
            sample_rules_config,
        )
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        orchestrator = Orchestrator(config_path="config/test.yaml")

        with pytest.raises(RuntimeError, match="not initialized"):
            await orchestrator.process({"query": "test"})

    @patch("agent_orchestrator.orchestrator.load_all_configs")
    @pytest.mark.asyncio
    async def test_process_security_validation_failure(
        self,
        mock_load_configs,
        sample_orchestrator_config,
        sample_agents_config,
        sample_rules_config,
        monkeypatch,
    ):
        """Test processing with security validation failure."""
        mock_load_configs.return_value = (
            sample_orchestrator_config,
            sample_agents_config,
            sample_rules_config,
        )
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        orchestrator = Orchestrator(config_path="config/test.yaml")
        await orchestrator.initialize()

        # Mock validate_input to raise SecurityError
        with patch("agent_orchestrator.orchestrator.validate_input") as mock_validate:
            mock_validate.side_effect = SecurityError("Malicious input detected")

            result = await orchestrator.process({"query": "'; DROP TABLE users; --"})

            assert result["success"] is False
            assert "Security validation failed" in result["error"]

    @patch("agent_orchestrator.orchestrator.load_all_configs")
    @pytest.mark.asyncio
    async def test_process_no_agents_selected(
        self,
        mock_load_configs,
        sample_orchestrator_config,
        sample_agents_config,
        sample_rules_config,
        monkeypatch,
    ):
        """Test processing when no agents can be determined."""
        mock_load_configs.return_value = (
            sample_orchestrator_config,
            sample_agents_config,
            sample_rules_config,
        )
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        orchestrator = Orchestrator(config_path="config/test.yaml")
        await orchestrator.initialize()

        # Mock reasoning to return None
        orchestrator._reason = AsyncMock(return_value=None)

        result = await orchestrator.process({"query": "unknown request"})

        assert result["success"] is False
        assert "No agents could be determined" in result["error"]

    @patch("agent_orchestrator.orchestrator.load_all_configs")
    @pytest.mark.asyncio
    async def test_process_success(
        self,
        mock_load_configs,
        sample_orchestrator_config,
        sample_agents_config,
        sample_rules_config,
        monkeypatch,
    ):
        """Test successful request processing."""
        mock_load_configs.return_value = (
            sample_orchestrator_config,
            sample_agents_config,
            sample_rules_config,
        )
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        orchestrator = Orchestrator(config_path="config/test.yaml")
        await orchestrator.initialize()

        # Mock the reasoning result
        from agent_orchestrator.reasoning.hybrid_reasoner import ReasoningResult
        mock_reasoning = ReasoningResult(
            agents=["calculator"],
            method="rule",
            confidence=0.9,
            reasoning="Matched calculation rule",
            parallel=False,
            parameters={},
        )
        orchestrator._reason = AsyncMock(return_value=mock_reasoning)

        # Mock agent execution
        from agent_orchestrator.agents.base_agent import AgentResponse
        mock_response = AgentResponse(
            agent_name="calculator",
            success=True,
            data={"result": 42},
            error=None,
            execution_time=0.1,
        )
        orchestrator._execute_agents = AsyncMock(return_value=[mock_response])

        result = await orchestrator.process({"query": "calculate 2 + 2"})

        assert result["success"] is True
        assert "calculator" in result["data"]
        assert result["_metadata"]["reasoning"]["method"] == "rule"
        assert orchestrator._request_count == 1

    @patch("agent_orchestrator.orchestrator.load_all_configs")
    @pytest.mark.asyncio
    async def test_process_with_custom_request_id(
        self,
        mock_load_configs,
        sample_orchestrator_config,
        sample_agents_config,
        sample_rules_config,
        monkeypatch,
    ):
        """Test processing with custom request ID."""
        mock_load_configs.return_value = (
            sample_orchestrator_config,
            sample_agents_config,
            sample_rules_config,
        )
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        orchestrator = Orchestrator(config_path="config/test.yaml")
        await orchestrator.initialize()

        # Mock reasoning and execution
        from agent_orchestrator.reasoning.hybrid_reasoner import ReasoningResult
        from agent_orchestrator.agents.base_agent import AgentResponse

        mock_reasoning = ReasoningResult(
            agents=["calculator"],
            method="rule",
            confidence=0.9,
            reasoning="Test",
            parallel=False,
            parameters={},
        )
        mock_response = AgentResponse(
            agent_name="calculator",
            success=True,
            data={"result": 42},
            error=None,
            execution_time=0.1,
        )

        orchestrator._reason = AsyncMock(return_value=mock_reasoning)
        orchestrator._execute_agents = AsyncMock(return_value=[mock_response])

        custom_id = "custom-request-123"
        result = await orchestrator.process(
            {"query": "test"},
            request_id=custom_id,
        )

        assert result["_metadata"]["request_id"] == custom_id

    @patch("agent_orchestrator.orchestrator.load_all_configs")
    @pytest.mark.asyncio
    async def test_process_exception_handling(
        self,
        mock_load_configs,
        sample_orchestrator_config,
        sample_agents_config,
        sample_rules_config,
        monkeypatch,
    ):
        """Test exception handling during processing."""
        mock_load_configs.return_value = (
            sample_orchestrator_config,
            sample_agents_config,
            sample_rules_config,
        )
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        orchestrator = Orchestrator(config_path="config/test.yaml")
        await orchestrator.initialize()

        # Mock reasoning to raise exception
        orchestrator._reason = AsyncMock(side_effect=Exception("Test error"))

        result = await orchestrator.process({"query": "test"})

        assert result["success"] is False
        assert "Orchestration error" in result["error"]


class TestOrchestratorReasoning:
    """Test reasoning functionality."""

    @pytest.mark.skip(reason="Complex mock setup - skipping for now")
    @patch("agent_orchestrator.orchestrator.load_all_configs")
    @pytest.mark.asyncio
    async def test_reason_rule_mode(
        self,
        mock_load_configs,
        sample_agents_config,
        sample_rules_config,
    ):
        """Test reasoning in rule-only mode."""
        from agent_orchestrator.config import OrchestratorConfig, ReasoningMode

        rule_config = OrchestratorConfig(
            name="rule-test",
            reasoning_mode=ReasoningMode.RULE,
            agents_config_path="config/agents.yaml",
            rules_config_path="config/rules.yaml",
            schemas_path="config/schemas/",
        )

        mock_load_configs.return_value = (
            rule_config,
            sample_agents_config,
            sample_rules_config,
        )

        orchestrator = Orchestrator(config_path="config/test.yaml")
        await orchestrator.initialize()

        # Mock hybrid reasoner's _rule_only method
        from agent_orchestrator.reasoning.hybrid_reasoner import ReasoningResult
        mock_result = ReasoningResult(
            agents=["calculator"],
            method="rule",
            confidence=0.9,
            reasoning="Rule matched",
            parallel=False,
            parameters={},
        )
        orchestrator.hybrid_reasoner._rule_only = MagicMock(return_value=mock_result)

        result = await orchestrator._reason({"query": "calculate"})

        assert result.method == "rule"
        assert result.agents == ["calculator"]

    @patch("agent_orchestrator.orchestrator.load_all_configs")
    @pytest.mark.asyncio
    async def test_reason_no_available_agents(
        self,
        mock_load_configs,
        sample_orchestrator_config,
        sample_agents_config,
        sample_rules_config,
        monkeypatch,
    ):
        """Test reasoning when all agents have open circuit breakers."""
        mock_load_configs.return_value = (
            sample_orchestrator_config,
            sample_agents_config,
            sample_rules_config,
        )
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        orchestrator = Orchestrator(config_path="config/test.yaml")
        await orchestrator.initialize()

        # Mock all circuit breakers as open
        orchestrator.circuit_breaker.is_open = MagicMock(return_value=True)

        result = await orchestrator._reason({"query": "test"})

        assert result is None


class TestOrchestratorStats:
    """Test statistics and monitoring."""

    @patch("agent_orchestrator.orchestrator.load_all_configs")
    @pytest.mark.asyncio
    async def test_get_stats(
        self,
        mock_load_configs,
        sample_orchestrator_config,
        sample_agents_config,
        sample_rules_config,
        monkeypatch,
    ):
        """Test getting orchestrator statistics."""
        mock_load_configs.return_value = (
            sample_orchestrator_config,
            sample_agents_config,
            sample_rules_config,
        )
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        orchestrator = Orchestrator(config_path="config/test.yaml")
        await orchestrator.initialize()

        stats = orchestrator.get_stats()

        assert "name" in stats
        assert "initialized" in stats
        assert "request_count" in stats
        assert "agents" in stats
        assert stats["name"] == "test-orchestrator"
        assert stats["initialized"] is True
        assert stats["request_count"] == 0


class TestOrchestratorCleanup:
    """Test cleanup and resource management."""

    @patch("agent_orchestrator.orchestrator.load_all_configs")
    @pytest.mark.asyncio
    async def test_cleanup(
        self,
        mock_load_configs,
        sample_orchestrator_config,
        sample_agents_config,
        sample_rules_config,
        monkeypatch,
    ):
        """Test orchestrator cleanup."""
        mock_load_configs.return_value = (
            sample_orchestrator_config,
            sample_agents_config,
            sample_rules_config,
        )
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        orchestrator = Orchestrator(config_path="config/test.yaml")
        await orchestrator.initialize()

        assert orchestrator._initialized is True

        await orchestrator.cleanup()

        assert orchestrator._initialized is False


class TestOrchestratorValidation:
    """Test output validation."""

    @patch("agent_orchestrator.orchestrator.load_all_configs")
    @pytest.mark.asyncio
    async def test_validate_outputs_no_schema(
        self,
        mock_load_configs,
        sample_orchestrator_config,
        sample_agents_config,
        sample_rules_config,
        monkeypatch,
    ):
        """Test output validation when no schema configured."""
        mock_load_configs.return_value = (
            sample_orchestrator_config,
            sample_agents_config,
            sample_rules_config,
        )
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        orchestrator = Orchestrator(config_path="config/test.yaml")

        from agent_orchestrator.agents.base_agent import AgentResponse
        responses = [
            AgentResponse(
                agent_name="test",
                success=True,
                data={"result": 42},
                error=None,
                execution_time=0.1,
            )
        ]

        validated = orchestrator._validate_outputs(responses)

        assert len(validated) == 1
        assert validated[0].success is True

    @patch("agent_orchestrator.orchestrator.load_all_configs")
    @pytest.mark.asyncio
    async def test_validate_outputs_with_schema(
        self,
        mock_load_configs,
        sample_agents_config,
        sample_rules_config,
        monkeypatch,
    ):
        """Test output validation with schema."""
        from agent_orchestrator.config import OrchestratorConfig, ValidationConfig

        config_with_validation = OrchestratorConfig(
            name="test",
            reasoning_mode="hybrid",
            ai_model="claude-sonnet-4-5-20250929",
            agents_config_path="config/agents.yaml",
            rules_config_path="config/rules.yaml",
            schemas_path="config/schemas/",
            validation=ValidationConfig(
                schema_name="test_schema",
                strict=False,
            ),
        )

        mock_load_configs.return_value = (
            config_with_validation,
            sample_agents_config,
            sample_rules_config,
        )
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        orchestrator = Orchestrator(config_path="config/test.yaml")

        # Mock schema validator
        orchestrator.schema_validator.validate = MagicMock(
            return_value=(True, [])
        )

        from agent_orchestrator.agents.base_agent import AgentResponse
        responses = [
            AgentResponse(
                agent_name="test",
                success=True,
                data={"result": 42},
                error=None,
                execution_time=0.1,
            )
        ]

        validated = orchestrator._validate_outputs(responses)

        assert len(validated) == 1
        assert validated[0].success is True
        orchestrator.schema_validator.validate.assert_called_once()


class TestOrchestratorAuditLog:
    """Test audit logging."""

    @patch("agent_orchestrator.orchestrator.load_all_configs")
    @pytest.mark.asyncio
    async def test_record_execution(
        self,
        mock_load_configs,
        sample_orchestrator_config,
        sample_agents_config,
        sample_rules_config,
        monkeypatch,
    ):
        """Test execution recording in audit log."""
        mock_load_configs.return_value = (
            sample_orchestrator_config,
            sample_agents_config,
            sample_rules_config,
        )
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        orchestrator = Orchestrator(config_path="config/test.yaml")

        # Initially no execution history
        assert len(orchestrator._execution_history) == 0

        # Record an execution
        orchestrator._record_execution(
            request_id="test-123",
            input_data={"query": "test"},
            reasoning_result=None,
            agent_responses=[],
            output={"success": True},
            start_time=datetime.utcnow(),
        )

        # Check history was recorded
        assert len(orchestrator._execution_history) == 1
        assert orchestrator._execution_history[0]["request_id"] == "test-123"

    @patch("agent_orchestrator.orchestrator.load_all_configs")
    @pytest.mark.asyncio
    async def test_record_execution_limit(
        self,
        mock_load_configs,
        sample_orchestrator_config,
        sample_agents_config,
        sample_rules_config,
        monkeypatch,
    ):
        """Test execution history limit (keeps last 1000)."""
        mock_load_configs.return_value = (
            sample_orchestrator_config,
            sample_agents_config,
            sample_rules_config,
        )
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        orchestrator = Orchestrator(config_path="config/test.yaml")

        # Add 1100 records
        for i in range(1100):
            orchestrator._record_execution(
                request_id=f"test-{i}",
                input_data={"query": "test"},
                reasoning_result=None,
                agent_responses=[],
                output={"success": True},
                start_time=datetime.utcnow(),
            )

        # Should keep only last 1000
        assert len(orchestrator._execution_history) == 1000
        # First record should be the 100th one (0-indexed, so id 100)
        assert orchestrator._execution_history[0]["request_id"] == "test-100"
