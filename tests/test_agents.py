"""Tests for agent implementations."""

import pytest

from agent_orchestrator.agents import AgentRegistry, DirectAgent
from agent_orchestrator.config import DirectToolConfig


class TestDirectAgent:
    """Test direct agent implementation."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test agent initialization."""
        agent = DirectAgent(
            name="test-calc",
            capabilities=["math"],
            tool_config=DirectToolConfig(
                module="examples.sample_calculator",
                function="calculate",
                is_async=False,
            ),
        )

        await agent.initialize()

        assert agent.name == "test-calc"
        assert "math" in agent.capabilities
        assert agent._initialized is True

        await agent.cleanup()

    @pytest.mark.asyncio
    async def test_agent_call_success(self):
        """Test successful agent call."""
        agent = DirectAgent(
            name="test-calc",
            capabilities=["math"],
            tool_config=DirectToolConfig(
                module="examples.sample_calculator",
                function="calculate",
                is_async=False,
            ),
        )

        await agent.initialize()

        response = await agent.call({
            "operation": "add",
            "operands": [5, 3],
        })

        assert response.success is True
        assert response.data["result"] == 8
        assert response.agent_name == "test-calc"

        await agent.cleanup()

    @pytest.mark.asyncio
    async def test_agent_call_failure(self):
        """Test agent call with invalid input."""
        agent = DirectAgent(
            name="test-calc",
            capabilities=["math"],
            tool_config=DirectToolConfig(
                module="examples.sample_calculator",
                function="calculate",
                is_async=False,
            ),
        )

        await agent.initialize()

        response = await agent.call({
            "operation": "invalid",
            "operands": [1, 2],
        })

        assert response.success is False
        assert "error" in response.error.lower() or "unknown" in response.error.lower()

        await agent.cleanup()

    @pytest.mark.asyncio
    async def test_agent_health_check(self):
        """Test agent health check."""
        agent = DirectAgent(
            name="test-calc",
            capabilities=["math"],
            tool_config=DirectToolConfig(
                module="examples.sample_calculator",
                function="calculate",
                is_async=False,
            ),
        )

        await agent.initialize()
        is_healthy = await agent.health_check()

        assert is_healthy is True

        await agent.cleanup()


class TestAgentRegistry:
    """Test agent registry."""

    @pytest.mark.asyncio
    async def test_register_agent(self):
        """Test agent registration."""
        registry = AgentRegistry()

        agent = DirectAgent(
            name="test-agent",
            capabilities=["test"],
            tool_config=DirectToolConfig(
                module="examples.sample_calculator",
                function="calculate",
                is_async=False,
            ),
        )

        await registry.register(agent)

        assert registry.has_agent("test-agent")
        assert registry.count() == 1

        await registry.cleanup_all()

    @pytest.mark.asyncio
    async def test_get_by_capability(self):
        """Test retrieving agents by capability."""
        registry = AgentRegistry()

        agent1 = DirectAgent(
            name="calc",
            capabilities=["math"],
            tool_config=DirectToolConfig(
                module="examples.sample_calculator",
                function="calculate",
                is_async=False,
            ),
        )

        agent2 = DirectAgent(
            name="search",
            capabilities=["search"],
            tool_config=DirectToolConfig(
                module="examples.sample_search",
                function="search_documents",
                is_async=True,
            ),
        )

        await registry.register(agent1)
        await registry.register(agent2)

        math_agents = registry.get_by_capability("math")
        assert len(math_agents) == 1
        assert math_agents[0].name == "calc"

        await registry.cleanup_all()

    @pytest.mark.asyncio
    async def test_unregister_agent(self):
        """Test agent unregistration."""
        registry = AgentRegistry()

        agent = DirectAgent(
            name="test-agent",
            capabilities=["test"],
            tool_config=DirectToolConfig(
                module="examples.sample_calculator",
                function="calculate",
                is_async=False,
            ),
        )

        await registry.register(agent)
        assert registry.has_agent("test-agent")

        await registry.unregister("test-agent")
        assert not registry.has_agent("test-agent")
