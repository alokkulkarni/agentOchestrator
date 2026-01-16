"""
Agent registry for managing and discovering agents.

This module provides centralized management of all available agents,
including registration, discovery by capability, and health monitoring.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from .base_agent import AgentError, BaseAgent

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Central registry for managing all agents.

    Provides methods to register, unregister, and query agents by name or capability.
    Maintains agent health status and provides bulk operations.
    """

    def __init__(self) -> None:
        """Initialize empty agent registry."""
        self._agents: Dict[str, BaseAgent] = {}
        self._capability_index: Dict[str, List[str]] = {}
        self._initialized = False

    async def register(self, agent: BaseAgent, initialize: bool = True) -> None:
        """
        Register an agent in the registry.

        Args:
            agent: Agent instance to register
            initialize: Whether to call agent.initialize() (default: True)

        Raises:
            AgentError: If agent with same name already exists or initialization fails
        """
        if agent.name in self._agents:
            raise AgentError(f"Agent with name '{agent.name}' is already registered")

        logger.info(f"Registering agent: {agent.name} with capabilities: {agent.capabilities}")

        # Initialize agent if requested
        if initialize:
            try:
                await agent.initialize()
            except Exception as e:
                logger.error(f"Failed to initialize agent {agent.name}: {e}")
                raise AgentError(f"Agent initialization failed: {e}") from e

        # Add to registry
        self._agents[agent.name] = agent

        # Update capability index
        for capability in agent.capabilities:
            cap_lower = capability.lower()
            if cap_lower not in self._capability_index:
                self._capability_index[cap_lower] = []
            self._capability_index[cap_lower].append(agent.name)

        logger.info(f"Agent {agent.name} registered successfully")

    async def unregister(self, agent_name: str, cleanup: bool = True) -> None:
        """
        Unregister an agent from the registry.

        Args:
            agent_name: Name of agent to unregister
            cleanup: Whether to call agent.cleanup() (default: True)

        Raises:
            AgentError: If agent not found
        """
        if agent_name not in self._agents:
            raise AgentError(f"Agent '{agent_name}' not found in registry")

        agent = self._agents[agent_name]
        logger.info(f"Unregistering agent: {agent_name}")

        # Cleanup agent if requested
        if cleanup:
            try:
                await agent.cleanup()
            except Exception as e:
                logger.warning(f"Error during agent cleanup for {agent_name}: {e}")

        # Remove from capability index
        for capability in agent.capabilities:
            cap_lower = capability.lower()
            if cap_lower in self._capability_index:
                self._capability_index[cap_lower].remove(agent_name)
                if not self._capability_index[cap_lower]:
                    del self._capability_index[cap_lower]

        # Remove from registry
        del self._agents[agent_name]
        logger.info(f"Agent {agent_name} unregistered successfully")

    def get(self, agent_name: str) -> Optional[BaseAgent]:
        """
        Get agent by name.

        Args:
            agent_name: Name of agent to retrieve

        Returns:
            Agent instance or None if not found
        """
        return self._agents.get(agent_name)

    def get_by_capability(self, capability: str) -> List[BaseAgent]:
        """
        Get all agents that have a specific capability.

        Args:
            capability: Capability to search for

        Returns:
            List of agents with the capability
        """
        cap_lower = capability.lower()
        agent_names = self._capability_index.get(cap_lower, [])
        return [self._agents[name] for name in agent_names if name in self._agents]

    def get_all(self) -> List[BaseAgent]:
        """
        Get all registered agents.

        Returns:
            List of all agents
        """
        return list(self._agents.values())

    def get_all_names(self) -> List[str]:
        """
        Get names of all registered agents.

        Returns:
            List of agent names
        """
        return list(self._agents.keys())

    def has_agent(self, agent_name: str) -> bool:
        """
        Check if an agent is registered.

        Args:
            agent_name: Name of agent to check

        Returns:
            True if agent is registered
        """
        return agent_name in self._agents

    def count(self) -> int:
        """
        Get number of registered agents.

        Returns:
            Number of agents
        """
        return len(self._agents)

    async def health_check_all(self) -> Dict[str, bool]:
        """
        Perform health checks on all agents.

        Returns:
            Dictionary mapping agent names to health status (True=healthy)
        """
        logger.info("Performing health checks on all agents")
        results = {}

        # Run health checks in parallel
        health_check_tasks = [
            (name, agent.health_check())
            for name, agent in self._agents.items()
        ]

        for name, task in health_check_tasks:
            try:
                is_healthy = await task
                results[name] = is_healthy
                if not is_healthy:
                    logger.warning(f"Agent {name} failed health check")
            except Exception as e:
                logger.error(f"Health check error for agent {name}: {e}")
                results[name] = False

        healthy_count = sum(1 for v in results.values() if v)
        logger.info(f"Health check complete: {healthy_count}/{len(results)} agents healthy")

        return results

    async def initialize_all(self) -> None:
        """
        Initialize all registered agents.

        Calls initialize() on all agents in parallel.
        """
        if self._initialized:
            logger.warning("Registry already initialized")
            return

        logger.info("Initializing all agents")
        init_tasks = [agent.initialize() for agent in self._agents.values()]

        results = await asyncio.gather(*init_tasks, return_exceptions=True)

        for agent, result in zip(self._agents.values(), results):
            if isinstance(result, Exception):
                logger.error(f"Failed to initialize agent {agent.name}: {result}")
            else:
                logger.info(f"Agent {agent.name} initialized successfully")

        self._initialized = True

    async def cleanup_all(self) -> None:
        """
        Cleanup all registered agents.

        Calls cleanup() on all agents in parallel.
        """
        logger.info("Cleaning up all agents")
        cleanup_tasks = [agent.cleanup() for agent in self._agents.values()]

        results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        for agent, result in zip(self._agents.values(), results):
            if isinstance(result, Exception):
                logger.warning(f"Error during cleanup for agent {agent.name}: {result}")
            else:
                logger.info(f"Agent {agent.name} cleaned up successfully")

        self._initialized = False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics for all agents.

        Returns:
            Dictionary with registry-wide statistics
        """
        agent_stats = [agent.get_stats() for agent in self._agents.values()]

        return {
            "total_agents": len(self._agents),
            "capabilities": list(self._capability_index.keys()),
            "agents": agent_stats,
        }

    def __repr__(self) -> str:
        return f"AgentRegistry(agents={len(self._agents)}, capabilities={len(self._capability_index)})"
