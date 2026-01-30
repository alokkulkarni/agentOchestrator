"""
Structured JSON logging configuration for Agent Orchestrator.

Provides:
- JSON-formatted logs for machine parsing
- Automatic correlation ID and trace ID injection
- Log rotation (size-based and time-based)
- PII sanitization
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
import structlog
from pythonjsonlogger import jsonlogger


def setup_orchestrator_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_console: bool = True,
    json_format: bool = True,
    enable_rotation: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    sanitize_logs: bool = True,
) -> logging.Logger:
    """
    Setup structured logging for orchestrator.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None = no file logging)
        enable_console: Whether to log to console
        json_format: Whether to use JSON format
        enable_rotation: Whether to enable log rotation
        max_bytes: Maximum size per log file
        backup_count: Number of backup files to keep
        sanitize_logs: Whether to sanitize sensitive data

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
    processors.append(TraceIDProcessor())

    # Add correlation ID processor
    processors.append(CorrelationIDProcessor())

    # Add sanitization processor
    if sanitize_logs:
        processors.append(SanitizationProcessor())

    # Add JSON renderer
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
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        if enable_rotation:
            # Size-based rotation
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
            )

            # Time-based rotation (daily)
            timed_handler = logging.handlers.TimedRotatingFileHandler(
                log_file.replace(".log", ".daily.log"),
                when="midnight",
                interval=1,
                backupCount=30,  # Keep 30 days
            )
            timed_handler.setLevel(getattr(logging, log_level.upper()))
            timed_handler.setFormatter(formatter)
            root_logger.addHandler(timed_handler)
        else:
            file_handler = logging.FileHandler(log_file)

        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    return root_logger


class TraceIDProcessor:
    """Structlog processor to add trace ID to logs."""

    def __call__(self, logger, method_name, event_dict):
        """Add trace ID if available."""
        try:
            from .tracing import get_trace_id, get_span_id

            trace_id = get_trace_id()
            span_id = get_span_id()

            if trace_id:
                event_dict["trace_id"] = trace_id
            if span_id:
                event_dict["span_id"] = span_id
        except Exception:
            pass  # Tracing not initialized or not available

        return event_dict


class CorrelationIDProcessor:
    """Structlog processor to add correlation ID to logs."""

    def __call__(self, logger, method_name, event_dict):
        """Add correlation ID if available in context."""
        try:
            from .context import get_correlation_id

            correlation_id = get_correlation_id()
            if correlation_id:
                event_dict["correlation_id"] = correlation_id
        except Exception:
            pass

        return event_dict


class SanitizationProcessor:
    """Structlog processor to sanitize sensitive data from logs."""

    def __call__(self, logger, method_name, event_dict):
        """Sanitize sensitive data from event dict."""
        try:
            from .sanitization import sanitize_text, sanitize_dict

            # Sanitize event message if it's a string
            if "event" in event_dict and isinstance(event_dict["event"], str):
                event_dict["event"] = sanitize_text(event_dict["event"])

            # Sanitize dict values
            for key, value in event_dict.items():
                if isinstance(value, dict):
                    event_dict[key] = sanitize_dict(value)
                elif isinstance(value, str) and key in [
                    "api_key", "token", "secret", "password"
                ]:
                    event_dict[key] = "[REDACTED]"

        except Exception as e:
            # Don't fail logging if sanitization fails
            event_dict["sanitization_error"] = str(e)

        return event_dict


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)
