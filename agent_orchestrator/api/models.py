"""
API request/response models for orchestrator API.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request model for /v1/query endpoint."""

    query: str = Field(..., description="Query string or natural language request")
    session_id: Optional[str] = Field(None, description="Session ID for conversation tracking")
    validate_input: bool = Field(True, description="Enable input security validation")
    stream: bool = Field(True, description="Enable streaming response")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    # Additional fields that can be included for specific operations
    operation: Optional[str] = Field(None, description="Specific operation to perform")
    operands: Optional[List[Any]] = Field(None, description="Operands for operations")
    data: Optional[Any] = Field(None, description="Data to process")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filters for data operations")
    max_results: Optional[int] = Field(None, description="Maximum results for search")
    keywords: Optional[List[str]] = Field(None, description="Keywords for search")


class QueryResponse(BaseModel):
    """Response model for /v1/query endpoint (non-streaming)."""

    success: bool = Field(..., description="Whether the query was successful")
    data: Dict[str, Any] = Field(..., description="Response data from agents")
    request_id: str = Field(..., description="Unique request ID (correlation ID)")
    session_id: Optional[str] = Field(None, description="Session ID if provided")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Execution metadata")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="Errors if any")


class StreamEvent(BaseModel):
    """Streaming event model."""

    event: str = Field(..., description="Event type")
    data: Dict[str, Any] = Field(..., description="Event data")
    timestamp: float = Field(..., description="Event timestamp")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service health status")
    orchestrator: Dict[str, Any] = Field(..., description="Orchestrator info")
    agents: Dict[str, Any] = Field(..., description="Agent status")
    timestamp: float = Field(..., description="Health check timestamp")


class StatsResponse(BaseModel):
    """Statistics response."""

    name: str
    initialized: bool
    request_count: int
    agents: Dict[str, Any]
    reasoning: Dict[str, Any]
    cost_tracking: Optional[Dict[str, Any]] = None
    circuit_breakers: Optional[Dict[str, str]] = None
