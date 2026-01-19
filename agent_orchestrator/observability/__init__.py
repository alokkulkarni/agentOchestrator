"""
Observability utilities for Agent Orchestrator.

Provides comprehensive monitoring, tracing, and logging:
- Prometheus metrics for production monitoring
- OpenTelemetry distributed tracing with OTLP
- Cost tracking for AI reasoner calls
- PII sanitization for security
- Structured JSON logging with rotation
- Session and correlation ID tracking
"""

from .metrics import orchestrator_metrics
from .metrics_server import metrics_server
from .tracing import init_tracing, get_tracer, create_span, end_span, TracingContext
from .cost_tracking import orchestrator_cost_tracker
from .sanitization import sanitize_data
from .logging_config import setup_orchestrator_logging, get_logger
from .context import (
    get_correlation_id,
    get_session_id,
    set_correlation_id,
    set_session_id,
    RequestContext,
)

__all__ = [
    "orchestrator_metrics",
    "metrics_server",
    "init_tracing",
    "get_tracer",
    "create_span",
    "end_span",
    "TracingContext",
    "orchestrator_cost_tracker",
    "sanitize_data",
    "setup_orchestrator_logging",
    "get_logger",
    "get_correlation_id",
    "get_session_id",
    "set_correlation_id",
    "set_session_id",
    "RequestContext",
]
