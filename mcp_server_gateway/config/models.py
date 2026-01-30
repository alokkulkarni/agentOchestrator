
"""
Configuration models for the MCP Server Gateway.

This module defines Pydantic models for all configuration types used by the MCP Gateway.
"""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class ReasoningMode(str, Enum):
    """Reasoning strategy for server selection."""
    AI = "ai"  # Pure AI-based reasoning using LLM
    RULE = "rule"  # Rule-based pattern matching
    HYBRID = "hybrid"  # Combination of both (rule-first, AI fallback)


class RuleOperator(str, Enum):
    """Logical operators for rule composition."""
    AND = "and"
    OR = "or"
    NOT = "not"


class StdioConnectionConfig(BaseModel):
    """Configuration for Stdio MCP connection."""
    command: str = Field(..., description="Command to execute (e.g. 'python', 'node')")
    args: List[str] = Field(default_factory=list, description="Arguments for the command")
    env: Optional[Dict[str, str]] = Field(None, description="Environment variables")


class SSEConnectionConfig(BaseModel):
    """Configuration for SSE MCP connection."""
    url: str = Field(..., description="SSE endpoint URL")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="HTTP headers")

class HttpConnectionConfig(BaseModel):
    """Configuration for HTTP MCP connection."""
    url: str = Field(..., description="HTTP endpoint URL")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="HTTP headers")
    timeout: Optional[float] = Field(30.0, description="Request timeout")


class StreamableHttpConnectionConfig(BaseModel):
    """Configuration for Streamable HTTP MCP connection (SSE)."""
    url: str = Field(..., description="Streamable HTTP endpoint URL")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="HTTP headers")
    timeout: Optional[float] = Field(None, description="Request timeout")


class MCPServerConnectionConfig(BaseModel):
    """Configuration for MCP server connection."""
    type: Literal["stdio", "sse", "http", "streamable_http"] = Field(..., description="Connection type")
    stdio: Optional[StdioConnectionConfig] = Field(None, description="Stdio configuration")
    sse: Optional[SSEConnectionConfig] = Field(None, description="SSE configuration")
    http: Optional[HttpConnectionConfig] = Field(None, description="HTTP configuration")
    streamable_http: Optional[StreamableHttpConnectionConfig] = Field(None, description="Streamable HTTP configuration")

    @model_validator(mode="after")
    def validate_connection(self) -> "MCPServerConnectionConfig":
        if self.type == "stdio" and not self.stdio:
            raise ValueError("Stdio config required for type 'stdio'")
        if self.type == "sse" and not self.sse:
            raise ValueError("SSE config required for type 'sse'")
        if self.type == "http" and not self.http:
            raise ValueError("HTTP config required for type 'http'")
        if self.type == "streamable_http" and not self.streamable_http:
            raise ValueError("Streamable HTTP config required for type 'streamable_http'")
        return self


class AgentRole(BaseModel):
    """Role definition for a server/agent with constraints and guardrails."""
    name: str = Field(..., description="Role name (e.g., 'data-analyst')")
    description: str = Field(..., description="Role description and purpose")
    allowed_operations: List[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed operations (* for all)"
    )
    denied_operations: List[str] = Field(
        default_factory=list,
        description="Explicitly denied operations"
    )
    max_execution_time: Optional[int] = Field(
        None,
        description="Maximum execution time in seconds"
    )
    require_approval: bool = Field(False, description="Require approval")


class AgentConstraints(BaseModel):
    """Constraints for execution."""
    max_retries: Optional[int] = Field(None)
    timeout: Optional[int] = Field(None)
    output_sanitization: bool = Field(True)


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP Server."""
    name: str = Field(..., description="Unique identifier")
    connection: MCPServerConnectionConfig = Field(..., description="Connection details")
    capabilities: List[str] = Field(default_factory=list, description="Capabilities/tags")
    role: Optional[AgentRole] = Field(None, description="Role definition")
    constraints: Optional[AgentConstraints] = Field(None, description="Constraints")
    enabled: bool = Field(True, description="Whether this server is enabled")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")


class RuleCondition(BaseModel):
    field: str
    operator: Literal["contains", "equals", "regex", "exists"]
    value: Optional[str] = None


class RuleConfig(BaseModel):
    name: str
