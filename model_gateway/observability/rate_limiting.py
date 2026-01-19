"""
Rate limiting for Model Gateway with tracking.

Provides:
- Per-endpoint rate limiting
- Per-client rate limiting
- Custom rate limit rules
- Rate limit hit tracking and logging
- Integration with Prometheus metrics
"""

from typing import Optional, Dict, Callable
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
import time


class RateLimiter:
    """Rate limiter with tracking and logging."""

    def __init__(
        self,
        default_limits: str = "100/minute",
        enabled: bool = True,
        key_func: Optional[Callable] = None,
    ):
        """
        Initialize rate limiter.

        Args:
            default_limits: Default rate limits (e.g., "100/minute", "1000/hour")
            enabled: Whether rate limiting is enabled
            key_func: Function to extract client identifier from request
        """
        self.enabled = enabled
        self.default_limits = default_limits

        # Use provided key function or default to IP address
        self.key_func = key_func or get_remote_address

        # Initialize slowapi limiter
        self.limiter = Limiter(
            key_func=self.key_func,
            default_limits=[default_limits] if enabled else [],
            enabled=enabled,
        )

        # Tracking
        self.rate_limit_hits: Dict[str, int] = {}
        self.rate_limit_hits_by_client: Dict[str, int] = {}
        self.rate_limit_hits_by_endpoint: Dict[str, int] = {}
        self.last_reset_time = time.time()

    def get_client_id(self, request: Request) -> str:
        """
        Get client identifier from request.

        Args:
            request: FastAPI request object

        Returns:
            Client identifier string
        """
        # Try to get client ID from header first
        client_id = request.headers.get("X-Client-ID")
        if client_id:
            return f"client:{client_id}"

        # Try to get from API key
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # Hash the token for privacy
            import hashlib

            token = auth_header[7:]  # Remove "Bearer "
            hashed = hashlib.sha256(token.encode()).hexdigest()[:16]
            return f"token:{hashed}"

        # Fall back to IP address
        return f"ip:{self.key_func(request)}"

    def record_rate_limit_hit(
        self, endpoint: str, client_id: str, request: Optional[Request] = None
    ):
        """
        Record a rate limit hit for tracking.

        Args:
            endpoint: Endpoint that was rate limited
            client_id: Client identifier
            request: Optional request object
        """
        # Overall tracking
        key = f"{endpoint}:{client_id}"
        self.rate_limit_hits[key] = self.rate_limit_hits.get(key, 0) + 1

        # By client
        self.rate_limit_hits_by_client[client_id] = (
            self.rate_limit_hits_by_client.get(client_id, 0) + 1
        )

        # By endpoint
        self.rate_limit_hits_by_endpoint[endpoint] = (
            self.rate_limit_hits_by_endpoint.get(endpoint, 0) + 1
        )

        # Log the rate limit hit
        try:
            from .logging_config import get_structured_logger

            logger = get_structured_logger(__name__)
            logger.warning(
                "rate_limit_exceeded",
                endpoint=endpoint,
                client_id=client_id,
                total_hits=self.rate_limit_hits[key],
            )
        except Exception:
            pass  # Don't fail if logging fails

        # Record in metrics
        try:
            from .metrics import metrics_manager

            metrics_manager.record_rate_limit_hit(endpoint, client_id)
        except Exception:
            pass  # Don't fail if metrics fail

    def get_rate_limit_stats(self) -> Dict[str, any]:
        """
        Get rate limiting statistics.

        Returns:
            Dictionary with rate limit statistics
        """
        return {
            "enabled": self.enabled,
            "default_limits": self.default_limits,
            "total_rate_limit_hits": sum(self.rate_limit_hits.values()),
            "unique_clients_limited": len(self.rate_limit_hits_by_client),
            "hits_by_endpoint": dict(self.rate_limit_hits_by_endpoint),
            "hits_by_client": dict(self.rate_limit_hits_by_client),
            "since": self.last_reset_time,
        }

    def reset_stats(self):
        """Reset rate limiting statistics."""
        self.rate_limit_hits = {}
        self.rate_limit_hits_by_client = {}
        self.rate_limit_hits_by_endpoint = {}
        self.last_reset_time = time.time()

    def create_custom_limit(self, limits: str):
        """
        Create a custom rate limit decorator.

        Args:
            limits: Rate limit string (e.g., "10/minute")

        Returns:
            Rate limit decorator
        """
        return self.limiter.limit(limits)

    def exempt(self, func: Callable) -> Callable:
        """
        Exempt a route from rate limiting.

        Args:
            func: Route function to exempt

        Returns:
            Exempted function
        """
        return self.limiter.exempt(func)

    def get_remaining_limit(self, request: Request) -> Optional[int]:
        """
        Get remaining requests for client.

        Args:
            request: FastAPI request

        Returns:
            Number of remaining requests, or None if unlimited
        """
        if not self.enabled:
            return None

        try:
            # This is a simplified version - actual implementation would query Redis/backend
            # slowapi doesn't expose this directly, so this is an estimate
            return None  # Not directly available from slowapi
        except Exception:
            return None


class RateLimitMiddleware:
    """Middleware to handle rate limit exceeded exceptions."""

    def __init__(self, rate_limiter: RateLimiter):
        """
        Initialize rate limit middleware.

        Args:
            rate_limiter: RateLimiter instance
        """
        self.rate_limiter = rate_limiter

    async def __call__(self, request: Request, call_next):
        """
        Process request with rate limit tracking.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        try:
            response = await call_next(request)
            return response
        except RateLimitExceeded as e:
            # Extract endpoint and client info
            endpoint = request.url.path
            client_id = self.rate_limiter.get_client_id(request)

            # Record the hit
            self.rate_limiter.record_rate_limit_hit(endpoint, client_id, request)

            # Re-raise the exception (will be handled by FastAPI)
            raise


def get_rate_limiter() -> RateLimiter:
    """
    Get the global rate limiter instance.

    Returns:
        RateLimiter instance
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None
rate_limiter: Optional[RateLimiter] = None


def init_rate_limiting(
    default_limits: str = "100/minute",
    enabled: bool = True,
    key_func: Optional[Callable] = None,
) -> RateLimiter:
    """
    Initialize rate limiting.

    Args:
        default_limits: Default rate limits
        enabled: Whether to enable rate limiting
        key_func: Optional custom key function

    Returns:
        RateLimiter instance
    """
    global rate_limiter, _rate_limiter

    rate_limiter = RateLimiter(
        default_limits=default_limits, enabled=enabled, key_func=key_func
    )
    _rate_limiter = rate_limiter

    return rate_limiter
