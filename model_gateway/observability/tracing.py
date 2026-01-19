"""
OpenTelemetry distributed tracing for Model Gateway.

Provides distributed tracing with:
- Automatic span creation
- Trace context propagation
- Custom span attributes
- Trace export to OTLP collector
"""

import os
from typing import Optional, Dict, Any
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.trace import Status, StatusCode


# Global tracer instance
_tracer: Optional[trace.Tracer] = None
_tracer_provider: Optional[TracerProvider] = None


def init_tracing(
    service_name: str = "model-gateway",
    service_version: str = "1.0.0",
    otlp_endpoint: Optional[str] = None,
    enable_console: bool = False,
) -> TracerProvider:
    """
    Initialize OpenTelemetry tracing.

    Args:
        service_name: Name of the service
        service_version: Version of the service
        otlp_endpoint: OTLP collector endpoint (e.g., "http://localhost:4317")
        enable_console: Whether to enable console exporter for debugging

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
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

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
        raise RuntimeError(
            "Tracing not initialized. Call init_tracing() first."
        )
    return _tracer


def instrument_fastapi(app):
    """
    Instrument FastAPI application with automatic tracing.

    Args:
        app: FastAPI application instance
    """
    if _tracer_provider is None:
        raise RuntimeError(
            "Tracing not initialized. Call init_tracing() first."
        )

    FastAPIInstrumentor.instrument_app(app, tracer_provider=_tracer_provider)


def create_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    parent_context: Optional[trace.SpanContext] = None,
):
    """
    Create a new span with optional attributes.

    Args:
        name: Span name
        attributes: Optional attributes to add to span
        parent_context: Optional parent span context

    Returns:
        Span context manager
    """
    tracer = get_tracer()

    if parent_context:
        ctx = trace.set_span_in_context(trace.NonRecordingSpan(parent_context))
        span = tracer.start_span(name, context=ctx)
    else:
        span = tracer.start_span(name)

    if attributes:
        for key, value in attributes.items():
            span.set_attribute(key, value)

    return span


def add_span_attributes(span: trace.Span, attributes: Dict[str, Any]):
    """
    Add attributes to an existing span.

    Args:
        span: Span to add attributes to
        attributes: Dictionary of attributes
    """
    for key, value in attributes.items():
        # Convert complex types to strings
        if isinstance(value, (dict, list)):
            value = str(value)
        span.set_attribute(key, value)


def record_exception(span: trace.Span, exception: Exception):
    """
    Record an exception in a span.

    Args:
        span: Span to record exception in
        exception: Exception to record
    """
    span.record_exception(exception)
    span.set_status(Status(StatusCode.ERROR, str(exception)))


def set_span_success(span: trace.Span):
    """
    Mark span as successful.

    Args:
        span: Span to mark as successful
    """
    span.set_status(Status(StatusCode.OK))


def set_span_error(span: trace.Span, error_message: str):
    """
    Mark span as failed with error message.

    Args:
        span: Span to mark as failed
        error_message: Error description
    """
    span.set_status(Status(StatusCode.ERROR, error_message))


class TracingContext:
    """Context manager for creating traced operations."""

    def __init__(
        self,
        operation_name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize tracing context.

        Args:
            operation_name: Name of the operation
            attributes: Optional attributes
        """
        self.operation_name = operation_name
        self.attributes = attributes or {}
        self.span: Optional[trace.Span] = None

    def __enter__(self):
        """Start span on entering context."""
        self.span = create_span(self.operation_name, self.attributes)
        self.span.__enter__()
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End span on exiting context."""
        if self.span:
            if exc_val:
                record_exception(self.span, exc_val)
            else:
                set_span_success(self.span)
            self.span.__exit__(exc_type, exc_val, exc_tb)


def trace_operation(operation_name: str, **attributes):
    """
    Decorator to automatically trace a function.

    Args:
        operation_name: Name of the operation
        **attributes: Additional span attributes

    Returns:
        Decorated function
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            with TracingContext(operation_name, attributes):
                return func(*args, **kwargs)

        return wrapper

    return decorator


async def trace_async_operation(operation_name: str, **attributes):
    """
    Async context manager for traced operations.

    Args:
        operation_name: Name of the operation
        **attributes: Additional span attributes

    Returns:
        Async context manager
    """
    return TracingContext(operation_name, attributes)


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


def inject_trace_context(headers: Dict[str, str]) -> Dict[str, str]:
    """
    Inject trace context into HTTP headers for propagation.

    Args:
        headers: Existing headers dictionary

    Returns:
        Headers with trace context injected
    """
    from opentelemetry.propagate import inject

    inject(headers)
    return headers


def extract_trace_context(headers: Dict[str, str]) -> Optional[trace.SpanContext]:
    """
    Extract trace context from HTTP headers.

    Args:
        headers: Headers containing trace context

    Returns:
        SpanContext if found, None otherwise
    """
    from opentelemetry.propagate import extract

    ctx = extract(headers)
    span = trace.get_current_span(ctx)
    if span and span.get_span_context().is_valid:
        return span.get_span_context()
    return None
