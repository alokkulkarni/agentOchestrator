"""
MCP agent implementation for communicating with MCP servers.

This module provides an agent that connects to MCP (Model Context Protocol) servers
and executes tools/functions via the MCP protocol using FastMCP.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import aiohttp

from ..config.models import MCPConnectionConfig
from .base_agent import (
    AgentConnectionError,
    AgentExecutionError,
    AgentResponse,
    AgentTimeoutError,
    BaseAgent,
)

logger = logging.getLogger(__name__)


class MCPAgent(BaseAgent):
    """
    Agent that communicates with MCP servers.

    Uses the MCP protocol to discover and call tools on remote servers.
    Supports connection pooling, health checks, and automatic reconnection.
    """

    def __init__(
        self,
        name: str,
        capabilities: List[str],
        connection_config: MCPConnectionConfig,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize MCP agent.

        Args:
            name: Unique agent identifier
            capabilities: List of capabilities for this agent
            connection_config: MCP server connection configuration
            metadata: Additional metadata
        """
        super().__init__(name, capabilities, metadata)
        self.connection_config = connection_config
        self.server_url = connection_config.url
        self.timeout = connection_config.timeout or 30
        self.headers = connection_config.headers or {}

        # HTTP session for connection pooling
        self._session: Optional[aiohttp.ClientSession] = None
        self._available_tools: List[Dict[str, Any]] = []
        self._connected = False

    async def initialize(self) -> None:
        """
        Initialize MCP connection and discover available tools.

        Establishes HTTP session and queries the MCP server for available tools.
        """
        logger.info(f"Initializing MCP agent: {self.name} -> {self.server_url}")

        # Create HTTP session with timeout
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self._session = aiohttp.ClientSession(
            timeout=timeout,
            headers=self.headers
        )

        # Discover available tools from MCP server
        try:
            await self._discover_tools()
            self._connected = True
            self._is_healthy = True
            logger.info(f"MCP agent {self.name} initialized with {len(self._available_tools)} tools")
        except Exception as e:
            logger.error(f"Failed to initialize MCP agent {self.name}: {e}")
            self._connected = False
            self._is_healthy = False

            # Clean up session before raising exception
            if self._session:
                await self._session.close()
                self._session = None

            raise AgentConnectionError(f"MCP agent initialization failed: {e}") from e

    async def cleanup(self) -> None:
        """Close HTTP session and clean up resources."""
        logger.info(f"Cleaning up MCP agent: {self.name}")

        if self._session:
            await self._session.close()
            self._session = None

        self._connected = False
        self._is_healthy = False

    async def _discover_tools(self) -> None:
        """
        Discover available tools from MCP server.

        Queries the server's /tools endpoint to get list of available tools.
        """
        if not self._session:
            raise AgentConnectionError("HTTP session not initialized")

        try:
            # MCP servers typically expose tools at /tools endpoint
            tools_url = f"{self.server_url.rstrip('/')}/tools"
            async with self._session.get(tools_url) as response:
                if response.status == 200:
                    data = await response.json()
                    self._available_tools = data.get("tools", [])
                    logger.debug(f"Discovered tools for {self.name}: {[t.get('name') for t in self._available_tools]}")
                else:
                    logger.warning(
                        f"Failed to discover tools from {tools_url}: "
                        f"HTTP {response.status}"
                    )
                    self._available_tools = []
        except asyncio.TimeoutError as e:
            raise AgentTimeoutError(f"Tool discovery timed out for {self.name}") from e
        except aiohttp.ClientError as e:
            raise AgentConnectionError(f"Connection error during tool discovery: {e}") from e

    async def call(
        self,
        input_data: Dict[str, Any],
        timeout: Optional[int] = None,
    ) -> AgentResponse:
        """
        Execute agent by calling MCP server tool.

        Args:
            input_data: Input data containing:
                - tool: Name of tool to call (optional, defaults to first available)
                - parameters: Parameters for the tool
                - Any other data passed to the MCP server
            timeout: Optional timeout override

        Returns:
            AgentResponse with execution result
        """
        start_time = time.time()
        timeout = timeout or self.timeout

        if not self._connected or not self._session:
            return AgentResponse(
                success=False,
                error="MCP agent not connected",
                agent_name=self.name,
                execution_time=time.time() - start_time,
            )

        try:
            # Determine which tool to call
            tool_name = input_data.get("tool", None)
            if not tool_name and self._available_tools:
                tool_name = self._available_tools[0].get("name")

            if not tool_name:
                return AgentResponse(
                    success=False,
                    error="No tool specified and no default tool available",
                    agent_name=self.name,
                    execution_time=time.time() - start_time,
                )

            # Prepare request payload
            payload = {
                "tool": tool_name,
                "parameters": input_data.get("parameters", {}),
                **{k: v for k, v in input_data.items() if k not in ["tool", "parameters"]}
            }

            # Call MCP server
            call_url = f"{self.server_url.rstrip('/')}/call"
            logger.debug(f"Calling MCP tool {tool_name} at {call_url}")

            async with self._session.post(
                call_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                execution_time = time.time() - start_time

                if response.status == 200:
                    result_data = await response.json()
                    self.record_call(execution_time, success=True)

                    return AgentResponse(
                        success=True,
                        data=result_data,
                        agent_name=self.name,
                        execution_time=execution_time,
                        metadata={
                            "tool": tool_name,
                            "server_url": self.server_url,
                        }
                    )
                else:
                    error_text = await response.text()
                    self.record_call(execution_time, success=False)

                    return AgentResponse(
                        success=False,
                        error=f"MCP server error (HTTP {response.status}): {error_text}",
                        agent_name=self.name,
                        execution_time=execution_time,
                    )

        except asyncio.TimeoutError as e:
            execution_time = time.time() - start_time
            self.record_call(execution_time, success=False)
            logger.error(f"MCP call timeout for {self.name}: {e}")

            return AgentResponse(
                success=False,
                error=f"Agent call timed out after {timeout}s",
                agent_name=self.name,
                execution_time=execution_time,
            )

        except aiohttp.ClientError as e:
            execution_time = time.time() - start_time
            self.record_call(execution_time, success=False)
            logger.error(f"MCP connection error for {self.name}: {e}")

            return AgentResponse(
                success=False,
                error=f"Connection error: {str(e)}",
                agent_name=self.name,
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            self.record_call(execution_time, success=False)
            logger.error(f"Unexpected error in MCP agent {self.name}: {e}", exc_info=True)

            return AgentResponse(
                success=False,
                error=f"Unexpected error: {str(e)}",
                agent_name=self.name,
                execution_time=execution_time,
            )

    async def health_check(self) -> bool:
        """
        Perform health check on MCP server.

        Sends a request to the /health endpoint to verify server is responsive.

        Returns:
            True if server is healthy
        """
        if not self._session or not self._connected:
            return False

        try:
            health_url = f"{self.server_url.rstrip('/')}/health"
            async with self._session.get(
                health_url,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                is_healthy = response.status == 200
                self._is_healthy = is_healthy
                return is_healthy

        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            logger.warning(f"Health check failed for {self.name}: {e}")
            self._is_healthy = False
            return False

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of available tools from this MCP agent.

        Returns:
            List of tool definitions
        """
        return self._available_tools.copy()

    def is_connected(self) -> bool:
        """
        Check if agent is connected to MCP server.

        Returns:
            True if connected
        """
        return self._connected
