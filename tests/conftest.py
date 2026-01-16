"""
Pytest configuration and fixtures for tests.

This module provides reusable fixtures for testing the orchestrator.
"""

import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator, Dict

import pytest

from agent_orchestrator.agents import AgentRegistry, DirectAgent
from agent_orchestrator.config import (
    AgentConfig,
    AgentType,
    AgentsFileConfig,
    BedrockConfig,
    DirectToolConfig,
    OrchestratorConfig,
    RuleConfig,
    RuleCondition,
    RulesFileConfig,
)
from agent_orchestrator.reasoning import AIReasoner, BedrockReasoner, HybridReasoner, RuleEngine


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_api_key() -> str:
    """Provide mock API key for testing."""
    return os.getenv("ANTHROPIC_API_KEY", "test-api-key-mock")


@pytest.fixture
def sample_orchestrator_config() -> OrchestratorConfig:
    """Provide sample orchestrator configuration."""
    return OrchestratorConfig(
        name="test-orchestrator",
        reasoning_mode="hybrid",
        ai_model="claude-sonnet-4-5-20250929",
        max_parallel_agents=3,
        default_timeout=30,
        agents_config_path="config/agents.yaml",
        rules_config_path="config/rules.yaml",
        schemas_path="config/schemas/",
        log_level="DEBUG",
    )


@pytest.fixture
def sample_agent_config() -> AgentConfig:
    """Provide sample agent configuration."""
    return AgentConfig(
        name="test-calculator",
        type=AgentType.DIRECT,
        direct_tool=DirectToolConfig(
            module="examples.sample_calculator",
            function="calculate",
            is_async=False,
        ),
        capabilities=["math", "calculation"],
        fallback=None,
        enabled=True,
    )


@pytest.fixture
def sample_agents_config() -> AgentsFileConfig:
    """Provide sample agents file configuration."""
    return AgentsFileConfig(
        agents=[
            AgentConfig(
                name="calculator",
                type=AgentType.DIRECT,
                direct_tool=DirectToolConfig(
                    module="examples.sample_calculator",
                    function="calculate",
                    is_async=False,
                ),
                capabilities=["math", "calculation"],
                fallback=None,
                enabled=True,
            ),
            AgentConfig(
                name="search",
                type=AgentType.DIRECT,
                direct_tool=DirectToolConfig(
                    module="examples.sample_search",
                    function="search_documents",
                    is_async=True,
                ),
                capabilities=["search", "retrieval"],
                fallback=None,
                enabled=True,
            ),
        ]
    )


@pytest.fixture
def sample_rules_config() -> RulesFileConfig:
    """Provide sample rules configuration."""
    return RulesFileConfig(
        rules=[
            RuleConfig(
                name="math_rule",
                priority=100,
                conditions=[
                    RuleCondition(
                        field="query",
                        operator="contains",
                        value="calculate",
                        case_sensitive=False,
                    )
                ],
                logic="or",
                target_agents=["calculator"],
                confidence=0.9,
                enabled=True,
            ),
            RuleConfig(
                name="search_rule",
                priority=90,
                conditions=[
                    RuleCondition(
                        field="query",
                        operator="contains",
                        value="search",
                        case_sensitive=False,
                    )
                ],
                logic="or",
                target_agents=["search"],
                confidence=0.85,
                enabled=True,
            ),
        ]
    )


@pytest.fixture
async def agent_registry() -> AsyncGenerator[AgentRegistry, None]:
    """Provide agent registry with sample agents."""
    registry = AgentRegistry()

    # Create and register test agent
    agent = DirectAgent(
        name="test-calculator",
        capabilities=["math", "calculation"],
        tool_config=DirectToolConfig(
            module="examples.sample_calculator",
            function="calculate",
            is_async=False,
        ),
    )

    await registry.register(agent)

    yield registry

    await registry.cleanup_all()


@pytest.fixture
def rule_engine(sample_rules_config: RulesFileConfig) -> RuleEngine:
    """Provide configured rule engine."""
    return RuleEngine(sample_rules_config)


@pytest.fixture
def mock_input_data() -> Dict:
    """Provide sample input data for testing."""
    return {
        "query": "calculate 2 plus 2",
        "parameters": {
            "operation": "add",
            "operands": [2, 2],
        },
    }


@pytest.fixture
def mock_search_data() -> Dict:
    """Provide sample search input data."""
    return {
        "query": "search for python tutorials",
        "max_results": 5,
    }


@pytest.fixture
def sample_bedrock_config() -> BedrockConfig:
    """Provide sample Bedrock configuration."""
    return BedrockConfig(
        region="us-east-1",
        model_id="anthropic.claude-sonnet-3-5-v2-20241022",
        role_arn=None,
        session_name="test-orchestrator",
        aws_profile=None,
    )


@pytest.fixture
def sample_orchestrator_config_bedrock(sample_bedrock_config: BedrockConfig) -> OrchestratorConfig:
    """Provide sample orchestrator configuration using Bedrock."""
    return OrchestratorConfig(
        name="test-orchestrator-bedrock",
        reasoning_mode="hybrid",
        ai_provider="bedrock",
        bedrock=sample_bedrock_config,
        max_parallel_agents=3,
        default_timeout=30,
        agents_config_path="config/agents.yaml",
        rules_config_path="config/rules.yaml",
        schemas_path="config/schemas/",
        log_level="DEBUG",
    )


@pytest.fixture(params=["anthropic", "bedrock"])
def ai_provider(request) -> str:
    """Parameterized fixture for testing both AI providers."""
    return request.param


@pytest.fixture
def orchestrator_config_for_provider(
    ai_provider: str,
    sample_orchestrator_config: OrchestratorConfig,
    sample_orchestrator_config_bedrock: OrchestratorConfig,
) -> OrchestratorConfig:
    """Provide orchestrator config based on AI provider parameter."""
    if ai_provider == "anthropic":
        return sample_orchestrator_config
    else:
        return sample_orchestrator_config_bedrock
