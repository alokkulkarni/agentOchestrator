"""
Observability middleware for Model Gateway.

Provides:
- Correlation ID tracking across requests
- Session ID management
- Request/response logging
- Automatic metrics collection
- Trace context propagation
"""

import time
import uuid
from typing import Optional, Dict, Any
from contextvars import ContextVar
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import sys


# Context variables for request-scoped data
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
session_id_var: ContextVar[Optional[str]] = ContextVar("session_id", default=None)
request_start_time_var: ContextVar[Optional[float]] = ContextVar(
    "request_start_time", default=None
)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation IDs to requests.

    Correlation IDs help track requests across services and logs.
    """

    def __init__(
        self,
        app: ASGIApp,
        header_name: str = "X-Correlation-ID",
        generate_if_missing: bool = True,
    ):
        """
        Initialize correlation ID middleware.

        Args:
            app: ASGI application
            header_name: Header name for correlation ID
            generate_if_missing: Generate ID if not provided
        """
        super().__init__(app)
        self.header_name = header_name
        self.generate_if_missing = generate_if_missing

    async def dispatch(self, request: Request, call_next):
        """
        Add correlation ID to request context.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response with correlation ID header
        """
        # Get or generate correlation ID
        correlation_id = request.headers.get(self.header_name)

        if not correlation_id and self.generate_if_missing:
            correlation_id = str(uuid.uuid4())

        # Store in context
        correlation_id_var.set(correlation_id)

        # Add to request state for easy access
        request.state.correlation_id = correlation_id

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        if correlation_id:
            response.headers[self.header_name] = correlation_id

        return response


class SessionTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track sessions across multiple requests.

    Sessions help identify returning clients and conversation context.
    """

    def __init__(
        self,
        app: ASGIApp,
        header_name: str = "X-Session-ID",
        cookie_name: str = "session_id",
        generate_if_missing: bool = True,
    ):
        """
        Initialize session tracking middleware.

        Args:
            app: ASGI application
            header_name: Header name for session ID
            cookie_name: Cookie name for session ID
            generate_if_missing: Generate ID if not provided
        """
        super().__init__(app)
        self.header_name = header_name
        self.cookie_name = cookie_name
        self.generate_if_missing = generate_if_missing
        self.active_sessions: Dict[str, float] = {}  # session_id -> last_seen

    async def dispatch(self, request: Request, call_next):
        """
        Track session for request.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response with session ID
        """
        # Try to get session ID from header or cookie
        session_id = request.headers.get(self.header_name)

        if not session_id:
            session_id = request.cookies.get(self.cookie_name)

        if not session_id and self.generate_if_missing:
            session_id = str(uuid.uuid4())

        # Store in context
        session_id_var.set(session_id)

        # Track active session
        if session_id:
            self.active_sessions[session_id] = time.time()
            request.state.session_id = session_id

        # Process request
        response = await call_next(request)

        # Add session ID to response
        if session_id:
            response.headers[self.header_name] = session_id
            # Optionally set cookie (commented out for now)
            # response.set_cookie(self.cookie_name, session_id, max_age=86400)

        return response

    def get_active_session_count(self) -> int:
        """
        Get count of active sessions.

        Returns:
            Number of active sessions
        """
        # Clean up old sessions (older than 1 hour)
        current_time = time.time()
        cutoff_time = current_time - 3600

        self.active_sessions = {
            sid: last_seen
            for sid, last_seen in self.active_sessions.items()
            if last_seen > cutoff_time
        }

        return len(self.active_sessions)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all requests with timing and metadata.
    """

    def __init__(
        self,
        app: ASGIApp,
        log_request_body: bool = False,
        log_response_body: bool = False,
        sanitize_logs: bool = True,
    ):
        """
        Initialize request logging middleware.

        Args:
            app: ASGI application
            log_request_body: Whether to log request body
            log_response_body: Whether to log response body
            sanitize_logs: Whether to sanitize sensitive data
        """
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.sanitize_logs = sanitize_logs

    async def dispatch(self, request: Request, call_next):
        """
        Log request and response.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        start_time = time.time()
        request_start_time_var.set(start_time)

        # Get correlation and session IDs
        correlation_id = getattr(request.state, "correlation_id", None)
        session_id = getattr(request.state, "session_id", None)

        # Get request info
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        try:
            # Process request
            response = await call_next(request)

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Log request
            try:
                from .logging_config import get_request_logger

                request_logger = get_request_logger()
                request_logger.log_request(
                    method=method,
                    path=path,
                    status_code=response.status_code,
                    latency_ms=latency_ms,
                    correlation_id=correlation_id,
                    session_id=session_id,
                    client_ip=client_ip,
                )
            except Exception:
                pass  # Don't fail request if logging fails

            # Record metrics
            try:
                from .metrics import metrics_manager

                # Determine provider from path or response
                provider = "unknown"
                if hasattr(response, "headers"):
                    provider = response.headers.get("X-Provider", "unknown")

                metrics_manager.record_request_size(
                    provider, request.headers.get("content-length", 0)
                )
                metrics_manager.record_response_size(
                    provider, response.headers.get("content-length", 0)
                )
            except Exception:
                pass  # Don't fail if metrics fail

            return response

        except Exception as e:
            # Log error
            latency_ms = (time.time() - start_time) * 1000

            try:
                from .logging_config import get_structured_logger

                logger = get_structured_logger(__name__)
                logger.error(
                    "request_failed",
                    method=method,
                    path=path,
                    latency_ms=round(latency_ms, 2),
                    error=str(e),
                    correlation_id=correlation_id,
                    session_id=session_id,
                )
            except Exception:
                pass

            raise


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically collect metrics for all requests.
    """

    def __init__(self, app: ASGIApp):
        """
        Initialize metrics middleware.

        Args:
            app: ASGI application
        """
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        """
        Collect metrics for request.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        start_time = time.time()

        # Get provider from path if available
        provider = "api"  # Default
        if "/v1/generate" in request.url.path:
            provider = "generate"

        try:
            from .metrics import metrics_manager

            # Increment active requests
            metrics_manager.increment_active_requests(provider)

            # Process request
            response = await call_next(request)

            # Calculate latency
            latency_seconds = time.time() - start_time

            # Record success
            status = "success" if response.status_code < 400 else "failed"
            model = response.headers.get("X-Model", "unknown")

            metrics_manager.record_request(
                provider=provider,
                model=model,
                status=status,
                latency_seconds=latency_seconds,
            )

            # Decrement active requests
            metrics_manager.decrement_active_requests(provider)

            return response

        except Exception as e:
            # Record failure
            try:
                from .metrics import metrics_manager

                latency_seconds = time.time() - start_time
                metrics_manager.record_failure(
                    provider=provider,
                    model="unknown",
                    error_type=type(e).__name__,
                    latency_seconds=latency_seconds,
                )
                metrics_manager.decrement_active_requests(provider)
            except Exception:
                pass

            raise


def get_correlation_id() -> Optional[str]:
    """
    Get current correlation ID from context.

    Returns:
        Correlation ID or None
    """
    return correlation_id_var.get()


def get_session_id() -> Optional[str]:
    """
    Get current session ID from context.

    Returns:
        Session ID or None
    """
    return session_id_var.get()


def get_request_start_time() -> Optional[float]:
    """
    Get request start time from context.

    Returns:
        Start time timestamp or None
    """
    return request_start_time_var.get()


def get_request_latency_ms() -> Optional[float]:
    """
    Get current request latency in milliseconds.

    Returns:
        Latency in ms or None
    """
    start_time = request_start_time_var.get()
    if start_time:
        return (time.time() - start_time) * 1000
    return None
