"""
Configuration models for the agent orchestrator.

This module defines Pydantic models for all configuration types used by the orchestrator.
All configurations are validated at load time to ensure type safety and correctness.
"""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class ReasoningMode(str, Enum):
    """Reasoning strategy for agent selection."""
    AI = "ai"  # Pure AI-based reasoning using LLM
    RULE = "rule"  # Rule-based pattern matching
    HYBRID = "hybrid"  # Combination of both (rule-first, AI fallback)


class AgentType(str, Enum):
    """Type of agent communication."""
    MCP = "mcp"  # MCP protocol communication
    DIRECT = "direct"  # Direct Python function call


class RuleOperator(str, Enum):
    """Logical operators for rule composition."""
    AND = "and"
    OR = "or"
    NOT = "not"


class MCPConnectionConfig(BaseModel):
    """Configuration for MCP server connection."""
    url: str = Field(..., description="MCP server URL (e.g., http://localhost:8080)")
    timeout: Optional[int] = Field(30, description="Connection timeout in seconds")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="HTTP headers")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format. Accepts HTTP/HTTPS URLs or 'stdio' for subprocess transport."""
        if v == "stdio":
            # Special case for MCP stdio transport (subprocess-based)
            return v
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http://, https://, or be 'stdio'")
        return v


class DirectToolConfig(BaseModel):
    """Configuration for direct Python tool."""
    module: str = Field(..., description="Python module path (e.g., 'examples.sample_calculator')")
    function: str = Field(..., description="Function name to call")
    is_async: bool = Field(False, description="Whether the function is async")

    @field_validator("module")
    @classmethod
    def validate_module(cls, v: str) -> str:
        """Ensure module path doesn't contain dangerous characters."""
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError("Module path contains invalid characters")
        return v


class AgentRole(BaseModel):
    """Role definition for an agent with constraints and guardrails."""
    name: str = Field(..., description="Role name (e.g., 'data-analyst', 'code-reviewer')")
    description: str = Field(..., description="Role description and purpose")
    allowed_operations: List[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed operations (* for all, or specific list)"
    )
    denied_operations: List[str] = Field(
        default_factory=list,
        description="Explicitly denied operations"
    )
    max_execution_time: Optional[int] = Field(
        None,
        description="Maximum execution time in seconds for this role"
    )
    max_input_size: Optional[int] = Field(
        None,
        description="Maximum input size in bytes"
    )
    require_approval: bool = Field(
        False,
        description="Whether this role requires human approval before execution"
    )
    guardrails: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom guardrails and constraints"
    )


class AgentConstraints(BaseModel):
    """Constraints and guardrails for agent execution."""
    max_retries: Optional[int] = Field(None, description="Override default max retries")
    timeout: Optional[int] = Field(None, description="Override default timeout")
    rate_limit: Optional[int] = Field(
        None,
        description="Maximum calls per minute (0 for unlimited)"
    )
    require_validation: bool = Field(
        False,
        description="Require output validation before returning"
    )
    allowed_input_fields: List[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed input fields (* for all)"
    )
    denied_input_fields: List[str] = Field(
        default_factory=list,
        description="Explicitly denied input fields"
    )
    output_sanitization: bool = Field(
        True,
        description="Sanitize output before returning"
    )
    log_level: str = Field("INFO", description="Logging level for this agent")


class AgentConfig(BaseModel):
    """Configuration for a single agent."""
    name: str = Field(..., description="Unique agent identifier")
    type: AgentType = Field(..., description="Agent communication type")
    connection: Optional[MCPConnectionConfig] = Field(None, description="MCP connection config")
    direct_tool: Optional[DirectToolConfig] = Field(None, description="Direct tool config")
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities/tags")
    role: Optional[AgentRole] = Field(None, description="Agent role with constraints")
    constraints: Optional[AgentConstraints] = Field(None, description="Agent constraints and guardrails")
    fallback: Optional[str] = Field(None, description="Name of fallback agent on failure")
    enabled: bool = Field(True, description="Whether this agent is enabled")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @model_validator(mode="after")
    def validate_config_match(self) -> "AgentConfig":
        """Ensure connection config matches agent type."""
        if self.type == AgentType.MCP and not self.connection:
            raise ValueError(f"Agent '{self.name}' of type 'mcp' requires connection config")
        if self.type == AgentType.DIRECT and not self.direct_tool:
            raise ValueError(f"Agent '{self.name}' of type 'direct' requires direct_tool config")
        return self


class RuleCondition(BaseModel):
    """Single condition in a routing rule."""
    field: str = Field(..., description="Input field to check (e.g., 'query', 'type')")
    operator: Literal["contains", "equals", "regex", "exists"] = Field(
        ..., description="Comparison operator"
    )
    value: Optional[str] = Field(None, description="Value to compare against")
    case_sensitive: bool = Field(False, description="Case-sensitive comparison")


class RuleConfig(BaseModel):
    """Routing rule for agent selection."""
    name: str = Field(..., description="Rule identifier")
    priority: int = Field(0, description="Rule priority (higher = evaluated first)")
    conditions: List[RuleCondition] = Field(..., description="Conditions to match")
    logic: RuleOperator = Field(RuleOperator.AND, description="How to combine conditions")
    target_agents: List[str] = Field(..., description="Agents to route to if matched")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Rule confidence score")
    enabled: bool = Field(True, description="Whether this rule is enabled")


class ValidationConfig(BaseModel):
    """Output validation configuration."""
    schema_name: Optional[str] = Field(None, description="JSON schema file to validate against")
    required_fields: List[str] = Field(default_factory=list, description="Required output fields")
    strict: bool = Field(False, description="Fail on validation errors vs. warn")


class RetryConfig(BaseModel):
    """Retry and fallback configuration."""
    max_attempts: int = Field(3, ge=1, le=10, description="Maximum retry attempts")
    exponential_backoff: bool = Field(True, description="Use exponential backoff")
    base_delay: float = Field(1.0, ge=0.1, le=10.0, description="Base delay between retries (seconds)")
    max_delay: float = Field(30.0, ge=1.0, le=300.0, description="Maximum delay between retries")
    retry_on_timeout: bool = Field(True, description="Retry on timeout errors")
    retry_on_connection_error: bool = Field(True, description="Retry on connection errors")


class BedrockConfig(BaseModel):
    """AWS Bedrock configuration for AI reasoning."""
    region: str = Field("us-east-1", description="AWS region for Bedrock")
    model_id: str = Field(
        "anthropic.claude-sonnet-3-5-v2-20241022",
        description="Bedrock model ID"
    )
    role_arn: Optional[str] = Field(None, description="Optional IAM role ARN for STS assume role")
    session_name: str = Field("agent-orchestrator", description="Session name for STS")
    aws_profile: Optional[str] = Field(None, description="AWS profile name to use")


class GatewayConfig(BaseModel):
    """Model Gateway configuration for AI reasoning."""
    url: str = Field("http://localhost:8000", description="Gateway base URL")
    provider: Optional[str] = Field(None, description="Provider to use through gateway (anthropic, bedrock)")
    model: Optional[str] = Field(None, description="Model to use (or None for provider default)")
    api_key: Optional[str] = Field(None, description="Optional API key for gateway authentication")


class OrchestratorConfig(BaseModel):
    """Main orchestrator configuration."""
    name: str = Field("agent-orchestrator", description="Orchestrator instance name")
    reasoning_mode: ReasoningMode = Field(ReasoningMode.HYBRID, description="Reasoning strategy")

    # AI Provider selection
    ai_provider: Literal["anthropic", "bedrock", "gateway"] = Field(
        "anthropic",
        description="AI provider for reasoning (anthropic, bedrock, or gateway)"
    )

    # Anthropic configuration
    ai_model: str = Field(
        "claude-sonnet-4-5-20250929",
        description="Claude model for AI reasoning (when using Anthropic)"
    )

    # Bedrock configuration
    bedrock: Optional[BedrockConfig] = Field(
        None,
        description="AWS Bedrock configuration (when using Bedrock)"
    )

    # Gateway configuration
    gateway: Optional[GatewayConfig] = Field(
        None,
        description="Model Gateway configuration (when using Gateway)"
    )
    max_parallel_agents: int = Field(
        3, ge=1, le=10,
        description="Maximum agents to call in parallel"
    )
    default_timeout: int = Field(
        30, ge=5, le=300,
        description="Default timeout for agent calls (seconds)"
    )
    retry_config: RetryConfig = Field(
        default_factory=RetryConfig,
        description="Retry and fallback configuration"
    )
    validation: ValidationConfig = Field(
        default_factory=ValidationConfig,
        description="Output validation configuration"
    )
    agents_config_path: str = Field(
        "config/agents.yaml",
        description="Path to agents configuration file"
    )
    rules_config_path: str = Field(
        "config/rules.yaml",
        description="Path to routing rules file"
    )
    schemas_path: str = Field(
        "config/schemas/",
        description="Directory containing JSON schemas"
    )
    log_level: str = Field("INFO", description="Logging level")
    enable_metrics: bool = Field(True, description="Enable execution metrics")
    enable_audit_log: bool = Field(True, description="Enable audit logging")

    # Response validation and hallucination detection
    validation_confidence_threshold: float = Field(
        0.7, ge=0.0, le=1.0,
        description="Minimum confidence score for response validation (0.0-1.0)"
    )
    validation_max_retries: int = Field(
        2, ge=0, le=5,
        description="Maximum retry attempts when validation fails"
    )

    # Per-query logging
    query_log_dir: str = Field(
        "logs/queries",
        description="Directory for per-query log files"
    )
    log_queries_to_file: bool = Field(
        True,
        description="Log detailed query information to files"
    )
    log_queries_to_console: bool = Field(
        False,
        description="Log query summaries to console"
    )


class AgentsFileConfig(BaseModel):
    """Root configuration for agents.yaml file."""
    agents: List[AgentConfig] = Field(..., description="List of agent configurations")

    def get_agent(self, name: str) -> Optional[AgentConfig]:
        """Get agent configuration by name."""
        return next((agent for agent in self.agents if agent.name == name), None)

    def get_agents_by_capability(self, capability: str) -> List[AgentConfig]:
        """Get all agents with a specific capability."""
        return [agent for agent in self.agents if capability in agent.capabilities]


class RulesFileConfig(BaseModel):
    """Root configuration for rules.yaml file."""
    rules: List[RuleConfig] = Field(..., description="List of routing rules")

    def get_sorted_rules(self) -> List[RuleConfig]:
        """Get rules sorted by priority (highest first)."""
        return sorted(
            [rule for rule in self.rules if rule.enabled],
            key=lambda r: r.priority,
            reverse=True
        )
