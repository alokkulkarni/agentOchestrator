"""
Structured JSON logging configuration for Model Gateway.

Provides:
- JSON-formatted logs
- Automatic field enrichment (timestamps, trace IDs, correlation IDs)
- Log rotation configuration
- Integration with tracing
- Correlation ID tracking
"""

import logging
import logging.handlers
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
import structlog
from pythonjsonlogger import jsonlogger


class CorrelationIDProcessor:
    """Structlog processor to add correlation ID to logs."""

    def __call__(self, logger, method_name, event_dict):
        """Add correlation ID if available in context."""
        from contextvars import ContextVar

        # Get correlation ID from context
        correlation_id_var: ContextVar[Optional[str]] = ContextVar(
            "correlation_id", default=None
        )
        correlation_id = correlation_id_var.get()

        if correlation_id:
            event_dict["correlation_id"] = correlation_id

        return event_dict


class TraceIDProcessor:
    """Structlog processor to add trace/span IDs to logs."""

    def __call__(self, logger, method_name, event_dict):
        """Add trace and span IDs if available."""
        try:
            from .tracing import get_trace_id, get_span_id

            trace_id = get_trace_id()
            span_id = get_span_id()

            if trace_id:
                event_dict["trace_id"] = trace_id
            if span_id:
                event_dict["span_id"] = span_id
        except Exception:
            # Tracing not initialized or not available
            pass

        return event_dict


class SanitizationProcessor:
    """Structlog processor to sanitize sensitive data from logs."""

    def __init__(self, sanitize_enabled: bool = True):
        """
        Initialize sanitization processor.

        Args:
            sanitize_enabled: Whether to enable sanitization
        """
        self.sanitize_enabled = sanitize_enabled

    def __call__(self, logger, method_name, event_dict):
        """Sanitize sensitive data from event dict."""
        if not self.sanitize_enabled:
            return event_dict

        try:
            from .sanitization import get_sanitizer

            sanitizer = get_sanitizer()

            # Sanitize event message if it's a string
            if "event" in event_dict and isinstance(event_dict["event"], str):
                event_dict["event"] = sanitizer.sanitize_text(event_dict["event"])

            # Sanitize any dict values
            for key, value in event_dict.items():
                if isinstance(value, dict):
                    event_dict[key] = sanitizer.sanitize_dict(value)
                elif isinstance(value, str) and key in [
                    "api_key",
                    "token",
                    "secret",
                    "password",
                ]:
                    event_dict[key] = "[REDACTED]"

        except Exception as e:
            # Don't fail logging if sanitization fails
            event_dict["sanitization_error"] = str(e)

        return event_dict


def setup_structured_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_console: bool = True,
    json_format: bool = True,
    enable_rotation: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    sanitize_logs: bool = True,
    include_trace_info: bool = True,
) -> logging.Logger:
    """
    Setup structured logging with JSON format and rotation.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None = no file logging)
        enable_console: Whether to log to console
        json_format: Whether to use JSON format
        enable_rotation: Whether to enable log rotation
        max_bytes: Maximum size per log file
        backup_count: Number of backup files to keep
        sanitize_logs: Whether to sanitize sensitive data
        include_trace_info: Whether to include trace/span IDs

    Returns:
        Configured logger instance
    """
    # Configure structlog processors
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Add trace ID processor
    if include_trace_info:
        processors.append(TraceIDProcessor())

    # Add correlation ID processor
    processors.append(CorrelationIDProcessor())

    # Add sanitization processor
    if sanitize_logs:
        processors.append(SanitizationProcessor(sanitize_enabled=True))

    # Add JSON renderer if enabled
    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    root_logger.handlers = []

    # Setup formatters
    if json_format:
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s",
            rename_fields={
                "asctime": "timestamp",
                "levelname": "level",
                "name": "logger",
            },
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler with rotation
    if log_file:
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        if enable_rotation:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
            )
        else:
            file_handler = logging.FileHandler(log_file)

        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Optionally setup timed rotation (daily)
    if log_file and enable_rotation:
        timed_handler = logging.handlers.TimedRotatingFileHandler(
            log_file.replace(".log", ".daily.log"),
            when="midnight",
            interval=1,
            backupCount=30,  # Keep 30 days
        )
        timed_handler.setLevel(getattr(logging, log_level.upper()))
        timed_handler.setFormatter(formatter)
        root_logger.addHandler(timed_handler)

    return root_logger


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)


class RequestLogger:
    """Logger for HTTP requests with automatic enrichment."""

    def __init__(self, logger: structlog.BoundLogger):
        """
        Initialize request logger.

        Args:
            logger: Structured logger instance
        """
        self.logger = logger

    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        latency_ms: float,
        correlation_id: Optional[str] = None,
        **extra_fields,
    ):
        """
        Log HTTP request.

        Args:
            method: HTTP method
            path: Request path
            status_code: HTTP status code
            latency_ms: Request latency in milliseconds
            correlation_id: Request correlation ID
            **extra_fields: Additional fields to log
        """
        log_data = {
            "event": "http_request",
            "method": method,
            "path": path,
            "status_code": status_code,
            "latency_ms": round(latency_ms, 2),
            **extra_fields,
        }

        if correlation_id:
            log_data["correlation_id"] = correlation_id

        # Log at appropriate level based on status code
        if status_code >= 500:
            self.logger.error(**log_data)
        elif status_code >= 400:
            self.logger.warning(**log_data)
        else:
            self.logger.info(**log_data)

    def log_generation_request(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        success: bool = True,
        correlation_id: Optional[str] = None,
        **extra_fields,
    ):
        """
        Log generation request.

        Args:
            provider: Provider name
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            latency_ms: Request latency
            success: Whether request was successful
            correlation_id: Request correlation ID
            **extra_fields: Additional fields
        """
        log_data = {
            "event": "generation_request",
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "latency_ms": round(latency_ms, 2),
            "success": success,
            **extra_fields,
        }

        if correlation_id:
            log_data["correlation_id"] = correlation_id

        if success:
            self.logger.info(**log_data)
        else:
            self.logger.error(**log_data)

    def log_fallback_event(
        self,
        from_provider: str,
        to_provider: str,
        reason: str,
        success: bool = True,
        correlation_id: Optional[str] = None,
    ):
        """
        Log fallback event.

        Args:
            from_provider: Original provider
            to_provider: Fallback provider
            reason: Reason for fallback
            success: Whether fallback was successful
            correlation_id: Request correlation ID
        """
        log_data = {
            "event": "provider_fallback",
            "from_provider": from_provider,
            "to_provider": to_provider,
            "reason": reason,
            "success": success,
        }

        if correlation_id:
            log_data["correlation_id"] = correlation_id

        if success:
            self.logger.warning(**log_data)
        else:
            self.logger.error(**log_data)


# Global logger instances
_root_logger: Optional[logging.Logger] = None
_structured_logger: Optional[structlog.BoundLogger] = None
_request_logger: Optional[RequestLogger] = None


def get_root_logger() -> logging.Logger:
    """Get root logger instance."""
    global _root_logger
    if _root_logger is None:
        _root_logger = setup_structured_logging()
    return _root_logger


def get_structured_logger(name: str = __name__) -> structlog.BoundLogger:
    """Get structured logger instance."""
    return get_logger(name)


def get_request_logger() -> RequestLogger:
    """Get request logger instance."""
    global _request_logger
    if _request_logger is None:
        logger = get_structured_logger("requests")
        _request_logger = RequestLogger(logger)
    return _request_logger
