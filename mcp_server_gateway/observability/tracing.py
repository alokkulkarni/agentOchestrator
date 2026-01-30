"""
OpenTelemetry distributed tracing for Agent Orchestrator.

Provides:
- OTLP export for traces
- Automatic span creation for queries, reasoning, and agent calls
- Trace context propagation
- Span attributes for debugging
"""

import os
from typing import Optional, Dict, Any
from contextvars import ContextVar
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import Status, StatusCode

# Global tracer instance
_tracer: Optional[trace.Tracer] = None
_tracer_provider: Optional[TracerProvider] = None

# Context variable for current span
_current_span: ContextVar[Optional[trace.Span]] = ContextVar("current_span", default=None)


def init_tracing(
    service_name: str = "agent-orchestrator",
    service_version: str = "1.0.0",
    otlp_endpoint: Optional[str] = None,
    enable_console: bool = False,
) -> TracerProvider:
    """
    Initialize OpenTelemetry tracing with OTLP export.

    Args:
        service_name: Name of the service
        service_version: Version of the service
        otlp_endpoint: OTLP collector endpoint (e.g., "http://localhost:4317")
        enable_console: Enable console exporter for debugging

    Returns:
        TracerProvider instance
    """
    global _tracer_provider, _tracer

    # Create resource with service information
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": os.getenv("ENVIRONMENT", "development"),
        }
    )

    # Create tracer provider
    _tracer_provider = TracerProvider(resource=resource)

    # Add OTLP exporter if endpoint provided
    if otlp_endpoint:
        try:
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        except Exception as e:
            import logging
            logging.warning(f"Failed to initialize OTLP exporter: {e}")

    # Add console exporter for debugging
    if enable_console:
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter
        console_exporter = ConsoleSpanExporter()
        _tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))

    # Set global tracer provider
    trace.set_tracer_provider(_tracer_provider)

    # Get tracer instance
    _tracer = trace.get_tracer(__name__)

    return _tracer_provider


def get_tracer() -> trace.Tracer:
    """
    Get the global tracer instance.

    Returns:
        Tracer instance

    Raises:
        RuntimeError: If tracing not initialized
    """
    if _tracer is None:
        raise RuntimeError("Tracing not initialized. Call init_tracing() first.")
    return _tracer


def create_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    set_as_current: bool = True,
) -> trace.Span:
    """
    Create a new span.

    Args:
        name: Span name
        attributes: Optional attributes
        set_as_current: Whether to set as current span in context

    Returns:
        Span instance
    """
    tracer = get_tracer()
    span = tracer.start_span(name)

    if attributes:
        for key, value in attributes.items():
            # Convert complex types to strings
            if isinstance(value, (dict, list)):
                value = str(value)
            span.set_attribute(key, value)

    if set_as_current:
        _current_span.set(span)

    return span


def get_current_span() -> Optional[trace.Span]:
    """Get current span from context."""
    return _current_span.get()


def end_span(span: trace.Span, success: bool = True, error: Optional[Exception] = None):
    """
    End a span with status.

    Args:
        span: Span to end
        success: Whether operation succeeded
        error: Optional error if failed
    """
    if error:
        span.record_exception(error)
        span.set_status(Status(StatusCode.ERROR, str(error)))
    elif success:
        span.set_status(Status(StatusCode.OK))
    else:
        span.set_status(Status(StatusCode.ERROR, "Operation failed"))

    span.end()

    # Clear from context if it's the current span
    if _current_span.get() == span:
        _current_span.set(None)


def add_span_event(span: trace.Span, name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Add an event to a span.

    Args:
        span: Span to add event to
        name: Event name
        attributes: Optional event attributes
    """
    span.add_event(name, attributes=attributes or {})


def get_trace_id() -> Optional[str]:
    """
    Get current trace ID as hex string.

    Returns:
        Trace ID or None if no active span
    """
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        return format(span.get_span_context().trace_id, "032x")
    return None


def get_span_id() -> Optional[str]:
    """
    Get current span ID as hex string.

    Returns:
        Span ID or None if no active span
    """
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        return format(span.get_span_context().span_id, "016x")
    return None


class TracingContext:
    """Context manager for creating traced operations."""

    def __init__(self, operation_name: str, attributes: Optional[Dict[str, Any]] = None):
        """
        Initialize tracing context.

        Args:
            operation_name: Name of the operation
            attributes: Optional span attributes
        """
        self.operation_name = operation_name
        self.attributes = attributes or {}
        self.span: Optional[trace.Span] = None

    def __enter__(self):
        """Start span on entering context."""
        self.span = create_span(self.operation_name, self.attributes)
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End span on exiting context."""
        if self.span:
            if exc_val:
                end_span(self.span, success=False, error=exc_val)
            else:
                end_span(self.span, success=True)
        return False  # Don't suppress exceptions


async def trace_async_operation(operation_name: str, **attributes):
    """
    Async context manager for traced operations.

    Args:
        operation_name: Name of the operation
        **attributes: Span attributes

    Returns:
        TracingContext instance
    """
    return TracingContext(operation_name, attributes)
