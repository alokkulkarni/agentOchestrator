"""
Retry and fallback logic for agent calls.

This module provides robust retry mechanisms with exponential backoff
and fallback strategies for handling agent failures.
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar

from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..agents.base_agent import (
    AgentConnectionError,
    AgentResponse,
    AgentTimeoutError,
    BaseAgent,
)
from ..config.models import RetryConfig

logger = logging.getLogger(__name__)

T = TypeVar("T")


class FallbackStrategy:
    """
    Fallback strategy for handling agent failures.

    Manages fallback agents and determines when to use them.
    """

    def __init__(self, agent_registry: Any):  # AgentRegistry type
        """
        Initialize fallback strategy.

        Args:
            agent_registry: Agent registry for looking up fallback agents
        """
        self.agent_registry = agent_registry
        self._fallback_attempts: Dict[str, int] = {}

    def get_fallback_agent(
        self,
        failed_agent_name: str,
        fallback_agent_name: Optional[str] = None,
    ) -> Optional[BaseAgent]:
        """
        Get fallback agent for a failed agent.

        Args:
            failed_agent_name: Name of agent that failed
            fallback_agent_name: Configured fallback agent name (if any)

        Returns:
            Fallback agent or None if not available
        """
        if not fallback_agent_name:
            logger.debug(f"No fallback configured for agent {failed_agent_name}")
            return None

        fallback_agent = self.agent_registry.get(fallback_agent_name)

        if not fallback_agent:
            logger.warning(
                f"Fallback agent '{fallback_agent_name}' not found for {failed_agent_name}"
            )
            return None

        # Track fallback attempts to prevent infinite loops
        attempts = self._fallback_attempts.get(failed_agent_name, 0)
        if attempts >= 3:
            logger.warning(
                f"Too many fallback attempts for {failed_agent_name}, stopping"
            )
            return None

        self._fallback_attempts[failed_agent_name] = attempts + 1
        logger.info(f"Using fallback agent '{fallback_agent_name}' for {failed_agent_name}")

        return fallback_agent

    def reset_attempts(self, agent_name: str) -> None:
        """Reset fallback attempt counter for an agent."""
        if agent_name in self._fallback_attempts:
            del self._fallback_attempts[agent_name]


class RetryHandler:
    """
    Retry handler for agent calls with configurable retry logic.

    Uses tenacity library for robust retry mechanisms with exponential backoff.
    """

    def __init__(
        self,
        retry_config: RetryConfig,
        fallback_strategy: Optional[FallbackStrategy] = None,
    ):
        """
        Initialize retry handler.

        Args:
            retry_config: Retry configuration
            fallback_strategy: Optional fallback strategy
        """
        self.config = retry_config
        self.fallback_strategy = fallback_strategy

        logger.info(
            f"Retry handler initialized: max_attempts={retry_config.max_attempts}, "
            f"backoff={retry_config.exponential_backoff}"
        )

    def _should_retry(self, exception: Exception) -> bool:
        """
        Determine if an exception should trigger a retry.

        Args:
            exception: Exception that occurred

        Returns:
            True if should retry
        """
        # Retry on timeout if configured
        if isinstance(exception, AgentTimeoutError) and self.config.retry_on_timeout:
            return True

        # Retry on connection error if configured
        if isinstance(exception, AgentConnectionError) and self.config.retry_on_connection_error:
            return True

        # Don't retry on other exceptions
        return False

    async def call_with_retry(
        self,
        agent: BaseAgent,
        input_data: Dict[str, Any],
        timeout: Optional[int] = None,
        fallback_agent_name: Optional[str] = None,
    ) -> AgentResponse:
        """
        Call agent with retry logic and fallback.

        Args:
            agent: Agent to call
            input_data: Input data for agent
            timeout: Optional timeout override
            fallback_agent_name: Name of fallback agent (if configured)

        Returns:
            AgentResponse from agent or fallback
        """
        logger.debug(f"Calling agent {agent.name} with retry (max_attempts={self.config.max_attempts})")

        # Configure retry behavior
        retry_config = {
            "stop": stop_after_attempt(self.config.max_attempts),
            "reraise": True,
        }

        # Add exponential backoff if enabled
        if self.config.exponential_backoff:
            retry_config["wait"] = wait_exponential(
                multiplier=self.config.base_delay,
                max=self.config.max_delay,
            )

        # Add retry condition
        retry_exceptions = []
        if self.config.retry_on_timeout:
            retry_exceptions.append(AgentTimeoutError)
        if self.config.retry_on_connection_error:
            retry_exceptions.append(AgentConnectionError)

        if retry_exceptions:
            retry_config["retry"] = retry_if_exception_type(tuple(retry_exceptions))

        # Attempt call with retry
        try:
            async for attempt in AsyncRetrying(**retry_config):
                with attempt:
                    logger.debug(
                        f"Agent {agent.name} call attempt {attempt.retry_state.attempt_number}"
                    )
                    response = await agent.call(input_data, timeout)

                    # If call failed, convert to exception for retry logic
                    if not response.success:
                        # Check if we should retry based on error type
                        if "timeout" in response.error.lower() and self.config.retry_on_timeout:
                            raise AgentTimeoutError(response.error)
                        elif "connection" in response.error.lower() and self.config.retry_on_connection_error:
                            raise AgentConnectionError(response.error)
                        else:
                            # Don't retry, return failed response
                            return response

                    return response

        except RetryError as e:
            logger.error(
                f"All retry attempts failed for agent {agent.name}: "
                f"{e.last_attempt.exception()}"
            )

            # Try fallback agent if available
            if self.fallback_strategy and fallback_agent_name:
                fallback_agent = self.fallback_strategy.get_fallback_agent(
                    agent.name, fallback_agent_name
                )

                if fallback_agent:
                    logger.info(f"Attempting fallback to agent {fallback_agent.name}")
                    try:
                        # Call fallback without retry to avoid infinite loops
                        response = await fallback_agent.call(input_data, timeout)
                        if response.success:
                            response.metadata["fallback_from"] = agent.name
                        return response
                    except Exception as fallback_error:
                        logger.error(f"Fallback agent {fallback_agent.name} also failed: {fallback_error}")

            # Return error response
            return AgentResponse(
                success=False,
                error=f"Agent call failed after {self.config.max_attempts} attempts: {e.last_attempt.exception()}",
                agent_name=agent.name,
                execution_time=0.0,
            )

        except Exception as e:
            logger.error(f"Unexpected error during retry for agent {agent.name}: {e}", exc_info=True)
            return AgentResponse(
                success=False,
                error=f"Unexpected error: {str(e)}",
                agent_name=agent.name,
                execution_time=0.0,
            )

    async def call_multiple_with_retry(
        self,
        agents: List[BaseAgent],
        input_data: Dict[str, Any],
        timeout: Optional[int] = None,
        fallback_map: Optional[Dict[str, str]] = None,
        parallel: bool = False,
    ) -> List[AgentResponse]:
        """
        Call multiple agents with retry logic.

        Args:
            agents: List of agents to call
            input_data: Input data for agents
            timeout: Optional timeout override
            fallback_map: Map of agent names to fallback agent names
            parallel: Whether to call agents in parallel

        Returns:
            List of agent responses
        """
        fallback_map = fallback_map or {}

        if parallel:
            logger.debug(f"Calling {len(agents)} agents in parallel with retry")
            tasks = [
                self.call_with_retry(
                    agent, input_data, timeout,
                    fallback_map.get(agent.name)
                )
                for agent in agents
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=False)
            return list(responses)
        else:
            logger.debug(f"Calling {len(agents)} agents sequentially with retry")
            responses = []
            for agent in agents:
                response = await self.call_with_retry(
                    agent, input_data, timeout,
                    fallback_map.get(agent.name)
                )
                responses.append(response)
            return responses


class CircuitBreaker:
    """
    Circuit breaker pattern for agent calls.

    Temporarily disables agents that are consistently failing to prevent
    cascading failures and reduce unnecessary load.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: float = 60.0,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            success_threshold: Number of successes to close circuit
            timeout: Time in seconds before attempting to close circuit
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout

        self._failure_counts: Dict[str, int] = {}
        self._success_counts: Dict[str, int] = {}
        self._circuit_open: Dict[str, bool] = {}
        self._open_time: Dict[str, float] = {}

        logger.debug("Circuit breaker initialized")

    def is_open(self, agent_name: str) -> bool:
        """
        Check if circuit is open for an agent.

        Args:
            agent_name: Agent name to check

        Returns:
            True if circuit is open (agent is disabled)
        """
        if agent_name not in self._circuit_open:
            return False

        if not self._circuit_open[agent_name]:
            return False

        # Check if timeout has elapsed to try half-open state
        import time
        if time.time() - self._open_time[agent_name] > self.timeout:
            logger.info(f"Circuit breaker for {agent_name} entering half-open state")
            return False

        return True

    def record_success(self, agent_name: str) -> None:
        """Record a successful agent call."""
        self._failure_counts[agent_name] = 0

        if self._circuit_open.get(agent_name, False):
            self._success_counts[agent_name] = self._success_counts.get(agent_name, 0) + 1

            if self._success_counts[agent_name] >= self.success_threshold:
                logger.info(f"Circuit breaker closed for {agent_name}")
                self._circuit_open[agent_name] = False
                self._success_counts[agent_name] = 0

    def record_failure(self, agent_name: str) -> None:
        """Record a failed agent call."""
        self._failure_counts[agent_name] = self._failure_counts.get(agent_name, 0) + 1
        self._success_counts[agent_name] = 0

        if self._failure_counts[agent_name] >= self.failure_threshold:
            logger.warning(
                f"Circuit breaker opened for {agent_name} "
                f"({self._failure_counts[agent_name]} consecutive failures)"
            )
            import time
            self._circuit_open[agent_name] = True
            self._open_time[agent_name] = time.time()

    def reset(self, agent_name: str) -> None:
        """Reset circuit breaker for an agent."""
        self._failure_counts[agent_name] = 0
        self._success_counts[agent_name] = 0
        self._circuit_open[agent_name] = False
        if agent_name in self._open_time:
            del self._open_time[agent_name]
