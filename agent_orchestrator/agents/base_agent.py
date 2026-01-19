"""
Base agent interface definition.

This module defines the abstract base class that all agents must implement,
ensuring consistent interaction patterns across different agent types.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional


class AgentError(Exception):
    """Base exception for agent-related errors."""
    pass


class AgentTimeoutError(AgentError):
    """Raised when an agent call times out."""
    pass


class AgentConnectionError(AgentError):
    """Raised when connection to an agent fails."""
    pass


class AgentExecutionError(AgentError):
    """Raised when agent execution fails."""
    pass


class AgentResponse:
    """
    Standardized response from an agent call.

    Attributes:
        success: Whether the agent call succeeded
        data: Response data from the agent
        error: Error message if call failed
        agent_name: Name of the agent that responded
        execution_time: Time taken to execute (seconds)
        metadata: Additional metadata about the response
    """

    def __init__(
        self,
        success: bool,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        agent_name: str = "",
        execution_time: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.success = success
        self.data = data or {}
        self.error = error
        self.agent_name = agent_name
        self.execution_time = execution_time
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "agent_name": self.agent_name,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return f"AgentResponse({status}, agent={self.agent_name}, time={self.execution_time:.3f}s)"


class BaseAgent(ABC):
    """
    Abstract base class for all agents.

    All agent implementations (MCP, direct tool, etc.) must inherit from this class
    and implement the required methods.
    """

    def __init__(
        self,
        name: str,
        capabilities: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize base agent.

        Args:
            name: Unique agent identifier
            capabilities: List of capabilities/tags for this agent
            metadata: Additional metadata about the agent
        """
        self.name = name
        self.capabilities = capabilities
        self.metadata = metadata or {}
        self._is_healthy = True
        self._call_count = 0
        self._error_count = 0
        self._total_execution_time = 0.0

    @abstractmethod
    async def call(self, input_data: Dict[str, Any], timeout: Optional[int] = None) -> AgentResponse:
        """
        Execute the agent with given input.

        Args:
            input_data: Input data for the agent
            timeout: Optional timeout in seconds (overrides default)

        Returns:
            AgentResponse with execution result

        Raises:
            AgentTimeoutError: If execution exceeds timeout
            AgentConnectionError: If connection to agent fails
            AgentExecutionError: If agent execution fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if agent is healthy and responsive.

        Returns:
            True if agent is healthy, False otherwise
        """
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the agent (connect, load resources, etc.).

        Called once when the agent is registered.
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """
        Clean up agent resources.

        Called when the agent is unregistered or orchestrator shuts down.
        """
        pass

    def has_capability(self, capability: str) -> bool:
        """
        Check if agent has a specific capability.

        Args:
            capability: Capability to check

        Returns:
            True if agent has the capability
        """
        return capability.lower() in [c.lower() for c in self.capabilities]

    def record_call(self, execution_time: float, success: bool) -> None:
        """
        Record metrics for an agent call.

        Args:
            execution_time: Time taken for execution (seconds)
            success: Whether the call succeeded
        """
        self._call_count += 1
        if not success:
            self._error_count += 1
        self._total_execution_time += execution_time

    def get_stats(self) -> Dict[str, Any]:
        """
        Get agent statistics.

        Returns:
            Dictionary with agent stats
        """
        avg_time = (
            self._total_execution_time / self._call_count
            if self._call_count > 0
            else 0.0
        )
        error_rate = (
            self._error_count / self._call_count
            if self._call_count > 0
            else 0.0
        )
        success_rate = (
            (self._call_count - self._error_count) / self._call_count
            if self._call_count > 0
            else 0.0
        )

        return {
            "name": self.name,
            "capabilities": self.capabilities,
            "is_healthy": self._is_healthy,
            "call_count": self._call_count,
            "error_count": self._error_count,
            "success_rate": success_rate,
            "error_rate": error_rate,
            "avg_execution_time": avg_time,
            "total_execution_time": self._total_execution_time,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, capabilities={self.capabilities})"
