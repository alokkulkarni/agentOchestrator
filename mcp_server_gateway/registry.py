
import asyncio
import logging
import os
from contextlib import AsyncExitStack
from typing import Dict, Any, List, Optional
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

from .config.models import MCPServerConfig, MCPServerConnectionConfig

logger = logging.getLogger(__name__)

class MCPServerConnection:
    """Manages a single connection to an MCP server."""
    
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.tools: List[Any] = []
        self._call_count = 0
        self._last_execution_time = 0.0
        
    @property
    def name(self) -> str:
        return self.config.name
        
    @property
    def capabilities(self) -> List[str]:
        return self.config.capabilities

    @property
    def metadata(self) -> Dict[str, Any]:
        return self.config.metadata
        
    def get_stats(self) -> Dict[str, Any]:
        """Return execution statistics (duck-typing BaseAgent compatibility)."""
        return {
            "call_count": self._call_count,
            "last_execution_time": self._last_execution_time,
            "connected": self.session is not None
        }

    async def connect(self):
        """Establish connection to the MCP server."""
        try:
            if self.config.connection.type == "stdio":
                await self._connect_stdio()
            elif self.config.connection.type == "sse":
                await self._connect_sse()
            elif self.config.connection.type == "http":
                await self._connect_http()
            elif self.config.connection.type == "streamable_http":
                await self._connect_streamable_http()
                
            # Initialize
            if self.session:
                await self.session.initialize()
                
                # List tools
                result = await self.session.list_tools()
                self.tools = result.tools
                logger.info(f"Connected to {self.config.name}. Found {len(self.tools)} tools.")
            else:
                 logger.error(f"Failed to create session for {self.config.name}")
                 
        except Exception as e:
            logger.error(f"Failed to connect to {self.config.name}: {e}")
            raise

    async def _connect_stdio(self):
        stdio_config = self.config.connection.stdio
        
        # Prepare environment
        env = os.environ.copy()
        if stdio_config.env:
            env.update(stdio_config.env)
            
        server_params = StdioServerParameters(
            command=stdio_config.command,
            args=stdio_config.args,
            env=env
        )
        
        read, write = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )

    async def _connect_sse(self):
        sse_config = self.config.connection.sse
        read, write = await self.exit_stack.enter_async_context(
            sse_client(sse_config.url, headers=sse_config.headers)
        )
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        
    async def _connect_http(self):
        """Connect via HTTP. Treating as SSE-capable request-response for now."""
        # Ideally, this would be a pure JSON-RPC over HTTP client without SSE subscription
        # but the MCP Python SDK primarily supports sse_client.
        # We will use sse_client but users can configure it as 'http' to indicate intention.
        http_config = self.config.connection.http
        read, write = await self.exit_stack.enter_async_context(
            sse_client(http_config.url, headers=http_config.headers, timeout=http_config.timeout)
        )
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )

    async def _connect_streamable_http(self):
        """Connect via Streamable HTTP (SSE)."""
        stream_config = self.config.connection.streamable_http
        read, write = await self.exit_stack.enter_async_context(
            sse_client(stream_config.url, headers=stream_config.headers, timeout=stream_config.timeout)
        )
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )

    async def disconnect(self):
        await self.exit_stack.aclose()
        self.session = None

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None):
        if not self.session:
            raise RuntimeError(f"Server {self.config.name} not connected")
        
        start_time = asyncio.get_event_loop().time()
        try:
            result = await self.session.call_tool(tool_name, arguments or {})
            self._call_count += 1
            return result
        finally:
            self._last_execution_time = asyncio.get_event_loop().time() - start_time


class ServerRegistry:
    """Registry for MCP Servers."""
    
    def __init__(self):
        self.servers: Dict[str, MCPServerConnection] = {}
        self.capability_index: Dict[str, List[str]] = {}

    async def register(self, config: MCPServerConfig):
        """Register and connect to a server."""
        connection = MCPServerConnection(config)
        await connection.connect()
        self.servers[config.name] = connection
        
        # Index capabilities
        for cap in config.capabilities:
            if cap not in self.capability_index:
                self.capability_index[cap] = []
            self.capability_index[cap].append(config.name)

    def get_server(self, name: str) -> Optional[MCPServerConnection]:
        return self.servers.get(name)
    
    def list_servers(self) -> Dict[str, MCPServerConnection]:
        return self.servers

    def get_servers_by_capability(self, capability: str) -> List[MCPServerConnection]:
        names = self.capability_index.get(capability, [])
        return [self.servers[name] for name in names if name in self.servers]

    async def cleanup(self):
        for server in self.servers.values():
            await server.disconnect()
        self.servers.clear()
        self.capability_index.clear()
