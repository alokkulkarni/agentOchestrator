"""
Direct tool agent implementation for calling Python functions.

This module provides an agent that wraps Python functions (sync or async)
and makes them callable through the agent interface.
"""

import asyncio
import importlib
import inspect
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from ..config.models import DirectToolConfig
from .base_agent import AgentExecutionError, AgentResponse, AgentTimeoutError, BaseAgent

logger = logging.getLogger(__name__)


class DirectAgent(BaseAgent):
    """
    Agent that wraps a Python function for direct calling.

    Supports both synchronous and asynchronous functions, with automatic
    type validation and docstring parsing for capability discovery.
    """

    def __init__(
        self,
        name: str,
        capabilities: List[str],
        tool_config: DirectToolConfig,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize direct tool agent.

        Args:
            name: Unique agent identifier
            capabilities: List of capabilities for this agent
            tool_config: Direct tool configuration (module, function)
            metadata: Additional metadata
        """
        super().__init__(name, capabilities, metadata)
        self.tool_config = tool_config
        self.module_path = tool_config.module
        self.function_name = tool_config.function
        self.is_async = tool_config.is_async

        self._function: Optional[Callable] = None
        self._function_signature: Optional[inspect.Signature] = None
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize agent by loading the Python function.

        Imports the module and retrieves the function, validates it's callable,
        and extracts its signature for parameter validation.
        """
        logger.info(f"Initializing direct tool agent: {self.name} ({self.module_path}.{self.function_name})")

        try:
            # Import module
            module = importlib.import_module(self.module_path)

            # Get function
            if not hasattr(module, self.function_name):
                raise AgentExecutionError(
                    f"Function '{self.function_name}' not found in module '{self.module_path}'"
                )

            self._function = getattr(module, self.function_name)

            # Validate it's callable
            if not callable(self._function):
                raise AgentExecutionError(
                    f"{self.module_path}.{self.function_name} is not callable"
                )

            # Check if it's async
            actual_is_async = inspect.iscoroutinefunction(self._function)
            if self.is_async != actual_is_async:
                logger.warning(
                    f"Function {self.function_name} async mismatch: "
                    f"configured={self.is_async}, actual={actual_is_async}. "
                    f"Using actual={actual_is_async}"
                )
                self.is_async = actual_is_async

            # Get function signature for parameter validation
            self._function_signature = inspect.signature(self._function)

            # Extract docstring for additional capabilities
            docstring = inspect.getdoc(self._function)
            if docstring:
                self.metadata["docstring"] = docstring

            self._initialized = True
            self._is_healthy = True
            logger.info(f"Direct tool agent {self.name} initialized successfully")

        except ImportError as e:
            logger.error(f"Failed to import module {self.module_path}: {e}")
            self._initialized = False
            self._is_healthy = False
            raise AgentExecutionError(f"Module import failed: {e}") from e
        except Exception as e:
            logger.error(f"Failed to initialize direct tool agent {self.name}: {e}")
            self._initialized = False
            self._is_healthy = False
            raise AgentExecutionError(f"Agent initialization failed: {e}") from e

    async def cleanup(self) -> None:
        """Clean up resources (nothing to do for direct tools)."""
        logger.info(f"Cleaning up direct tool agent: {self.name}")
        self._function = None
        self._function_signature = None
        self._initialized = False
        self._is_healthy = False

    def _validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate parameters against function signature.

        Args:
            parameters: Parameters to validate

        Returns:
            Validated parameters (may add defaults), filtered to only include
            parameters that the function accepts

        Raises:
            AgentExecutionError: If required parameters are missing
        """
        if not self._function_signature:
            return parameters

        # Get function parameter names
        func_params = set(self._function_signature.parameters.keys())

        # Filter parameters to only include those the function accepts
        filtered_params = {
            k: v for k, v in parameters.items()
            if k in func_params
        }

        try:
            # Try to bind filtered parameters to signature
            bound_args = self._function_signature.bind_partial(**filtered_params)
            bound_args.apply_defaults()
            return dict(bound_args.arguments)
        except TypeError as e:
            raise AgentExecutionError(f"Invalid parameters for {self.name}: {e}") from e

    async def call(
        self,
        input_data: Dict[str, Any],
        timeout: Optional[int] = None,
    ) -> AgentResponse:
        """
        Execute agent by calling the Python function.

        Args:
            input_data: Input data containing function parameters
            timeout: Optional timeout in seconds

        Returns:
            AgentResponse with execution result
        """
        start_time = time.time()
        timeout = timeout or 30  # Default timeout for direct tools

        if not self._initialized or not self._function:
            return AgentResponse(
                success=False,
                error="Direct tool agent not initialized",
                agent_name=self.name,
                execution_time=time.time() - start_time,
            )

        try:
            # Extract parameters from input_data
            # Support both direct parameters and nested under 'parameters' key
            if "parameters" in input_data:
                parameters = input_data["parameters"]
            else:
                # Filter out orchestrator meta keys only
                # The _validate_parameters method will filter to match function signature
                parameters = {
                    k: v for k, v in input_data.items()
                    if k not in ["tool", "agent", "timeout", "request_id"]
                }

            # Validate parameters
            validated_params = self._validate_parameters(parameters)

            logger.debug(f"Calling direct tool {self.name} with params: {list(validated_params.keys())}")

            # Call function with timeout
            try:
                if self.is_async:
                    # Call async function with timeout
                    result = await asyncio.wait_for(
                        self._function(**validated_params),
                        timeout=timeout
                    )
                else:
                    # Run sync function in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: self._function(**validated_params)),
                        timeout=timeout
                    )

                execution_time = time.time() - start_time
                self.record_call(execution_time, success=True)

                # Wrap result in standard format if it's not a dict
                if not isinstance(result, dict):
                    result = {"result": result}

                return AgentResponse(
                    success=True,
                    data=result,
                    agent_name=self.name,
                    execution_time=execution_time,
                    metadata={
                        "function": f"{self.module_path}.{self.function_name}",
                        "is_async": self.is_async,
                    }
                )

            except asyncio.TimeoutError as e:
                execution_time = time.time() - start_time
                self.record_call(execution_time, success=False)
                logger.error(f"Direct tool {self.name} timed out after {timeout}s")

                return AgentResponse(
                    success=False,
                    error=f"Function call timed out after {timeout}s",
                    agent_name=self.name,
                    execution_time=execution_time,
                )

        except AgentExecutionError as e:
            execution_time = time.time() - start_time
            self.record_call(execution_time, success=False)
            logger.error(f"Execution error in direct tool {self.name}: {e}")

            return AgentResponse(
                success=False,
                error=str(e),
                agent_name=self.name,
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            self.record_call(execution_time, success=False)
            logger.error(f"Unexpected error in direct tool {self.name}: {e}", exc_info=True)

            return AgentResponse(
                success=False,
                error=f"Unexpected error: {str(e)}",
                agent_name=self.name,
                execution_time=execution_time,
            )

    async def health_check(self) -> bool:
        """
        Check if agent is healthy.

        For direct tools, this just checks if the function is loaded.

        Returns:
            True if function is loaded and callable
        """
        is_healthy = self._initialized and self._function is not None and callable(self._function)
        self._is_healthy = is_healthy
        return is_healthy

    def get_function_info(self) -> Dict[str, Any]:
        """
        Get information about the wrapped function.

        Returns:
            Dictionary with function metadata
        """
        info = {
            "module": self.module_path,
            "function": self.function_name,
            "is_async": self.is_async,
            "initialized": self._initialized,
        }

        if self._function_signature:
            info["parameters"] = {
                name: {
                    "annotation": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any",
                    "default": str(param.default) if param.default != inspect.Parameter.empty else "Required",
                }
                for name, param in self._function_signature.parameters.items()
            }

        if "docstring" in self.metadata:
            info["docstring"] = self.metadata["docstring"]

        return info
