"""
Context management for correlation IDs and session IDs.

Provides thread-safe context variables for tracking:
- Correlation IDs (per-request tracking)
- Session IDs (multi-request conversation tracking)
- Request metadata
"""

import uuid
from contextvars import ContextVar
from typing import Optional, Dict, Any
import time

# Context variables for request-scoped data
_correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
_session_id_var: ContextVar[Optional[str]] = ContextVar("session_id", default=None)
_request_start_time_var: ContextVar[Optional[float]] = ContextVar("request_start_time", default=None)
_request_metadata_var: ContextVar[Dict[str, Any]] = ContextVar("request_metadata", default=None)

# Session tracking
_active_sessions: Dict[str, Dict[str, Any]] = {}


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


def generate_session_id() -> str:
    """Generate a new session ID."""
    return str(uuid.uuid4())


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Set correlation ID for current context.

    Args:
        correlation_id: Correlation ID (generates new if None)

    Returns:
        The correlation ID that was set
    """
    if correlation_id is None:
        correlation_id = generate_correlation_id()

    _correlation_id_var.set(correlation_id)
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """
    Get correlation ID from current context.

    Returns:
        Correlation ID or None
    """
    return _correlation_id_var.get()


def set_session_id(session_id: Optional[str] = None) -> str:
    """
    Set session ID for current context.

    Args:
        session_id: Session ID (generates new if None)

    Returns:
        The session ID that was set
    """
    if session_id is None:
        session_id = generate_session_id()

    _session_id_var.set(session_id)

    # Track session
    if session_id not in _active_sessions:
        _active_sessions[session_id] = {
            "session_id": session_id,
            "created_at": time.time(),
            "last_seen": time.time(),
            "query_count": 0,
        }
    else:
        _active_sessions[session_id]["last_seen"] = time.time()
        _active_sessions[session_id]["query_count"] += 1

    return session_id


def get_session_id() -> Optional[str]:
    """
    Get session ID from current context.

    Returns:
        Session ID or None
    """
    return _session_id_var.get()


def set_request_start_time(start_time: Optional[float] = None):
    """
    Set request start time for current context.

    Args:
        start_time: Start time timestamp (uses current time if None)
    """
    if start_time is None:
        start_time = time.time()

    _request_start_time_var.set(start_time)


def get_request_start_time() -> Optional[float]:
    """
    Get request start time from current context.

    Returns:
        Start time timestamp or None
    """
    return _request_start_time_var.get()


def get_request_duration_ms() -> Optional[float]:
    """
    Get request duration in milliseconds.

    Returns:
        Duration in ms or None if start time not set
    """
    start_time = _request_start_time_var.get()
    if start_time:
        return (time.time() - start_time) * 1000
    return None


def set_request_metadata(metadata: Dict[str, Any]):
    """
    Set request metadata for current context.

    Args:
        metadata: Metadata dictionary
    """
    _request_metadata_var.set(metadata)


def get_request_metadata() -> Optional[Dict[str, Any]]:
    """
    Get request metadata from current context.

    Returns:
        Metadata dictionary or None
    """
    return _request_metadata_var.get()


def clear_context():
    """Clear all context variables for current request."""
    _correlation_id_var.set(None)
    _session_id_var.set(None)
    _request_start_time_var.set(None)
    _request_metadata_var.set(None)


def get_active_session_count() -> int:
    """
    Get count of active sessions.

    Returns:
        Number of active sessions
    """
    # Clean up old sessions (older than 1 hour)
    current_time = time.time()
    cutoff_time = current_time - 3600

    global _active_sessions
    _active_sessions = {
        sid: data
        for sid, data in _active_sessions.items()
        if data["last_seen"] > cutoff_time
    }

    return len(_active_sessions)


def get_session_stats() -> Dict[str, Any]:
    """
    Get session statistics.

    Returns:
        Dictionary with session stats
    """
    active_count = get_active_session_count()

    if not _active_sessions:
        return {
            "active_sessions": 0,
            "total_queries": 0,
            "avg_queries_per_session": 0.0,
        }

    total_queries = sum(data["query_count"] for data in _active_sessions.values())
    avg_queries = total_queries / active_count if active_count > 0 else 0.0

    return {
        "active_sessions": active_count,
        "total_queries": total_queries,
        "avg_queries_per_session": round(avg_queries, 2),
    }


class RequestContext:
    """Context manager for request tracking."""

    def __init__(
        self,
        correlation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize request context.

        Args:
            correlation_id: Optional correlation ID
            session_id: Optional session ID
            metadata: Optional metadata
        """
        self.correlation_id = correlation_id
        self.session_id = session_id
        self.metadata = metadata or {}
        self.previous_correlation_id = None
        self.previous_session_id = None

    def __enter__(self):
        """Enter context and set IDs."""
        # Save previous IDs
        self.previous_correlation_id = get_correlation_id()
        self.previous_session_id = get_session_id()

        # Set new IDs
        set_correlation_id(self.correlation_id)
        set_session_id(self.session_id)
        set_request_start_time()
        set_request_metadata(self.metadata)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore previous IDs."""
        # Restore previous IDs
        _correlation_id_var.set(self.previous_correlation_id)
        _session_id_var.set(self.previous_session_id)
        return False  # Don't suppress exceptions
