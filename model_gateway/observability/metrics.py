"""
Prometheus metrics for Model Gateway.

Provides comprehensive metrics tracking including:
- Request counters (total, success, failure)
- Latency histograms with percentiles (p50, p95, p99)
- Token usage tracking
- Provider-specific metrics
- Cost tracking
"""

import time
from typing import Dict, Optional
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    CollectorRegistry,
    generate_latest,
)


class MetricsManager:
    """Manages all Prometheus metrics for the gateway."""

    def __init__(self):
        """Initialize metrics manager with all metric collectors."""
        self.registry = CollectorRegistry()

        # Request counters
        self.requests_total = Counter(
            "gateway_requests_total",
            "Total number of requests",
            ["provider", "model", "status"],
            registry=self.registry,
        )

        self.requests_success = Counter(
            "gateway_requests_success_total",
            "Total number of successful requests",
            ["provider", "model"],
            registry=self.registry,
        )

        self.requests_failed = Counter(
            "gateway_requests_failed_total",
            "Total number of failed requests",
            ["provider", "model", "error_type"],
            registry=self.registry,
        )

        # Fallback tracking
        self.fallback_triggered = Counter(
            "gateway_fallback_triggered_total",
            "Number of times fallback was triggered",
            ["from_provider", "to_provider"],
            registry=self.registry,
        )

        self.fallback_success = Counter(
            "gateway_fallback_success_total",
            "Number of successful fallbacks",
            ["from_provider", "to_provider"],
            registry=self.registry,
        )

        # Latency histograms (with buckets for percentile calculation)
        self.request_latency = Histogram(
            "gateway_request_duration_seconds",
            "Request duration in seconds",
            ["provider", "model"],
            buckets=(
                0.01,
                0.025,
                0.05,
                0.075,
                0.1,
                0.25,
                0.5,
                0.75,
                1.0,
                2.5,
                5.0,
                7.5,
                10.0,
                15.0,
                20.0,
                30.0,
            ),
            registry=self.registry,
        )

        self.provider_latency = Histogram(
            "gateway_provider_duration_seconds",
            "Provider-specific request duration in seconds",
            ["provider", "model", "attempt"],
            buckets=(
                0.01,
                0.025,
                0.05,
                0.075,
                0.1,
                0.25,
                0.5,
                0.75,
                1.0,
                2.5,
                5.0,
                7.5,
                10.0,
                15.0,
                20.0,
                30.0,
            ),
            registry=self.registry,
        )

        # Token usage metrics
        self.tokens_consumed = Counter(
            "gateway_tokens_consumed_total",
            "Total tokens consumed",
            ["provider", "model", "token_type"],
            registry=self.registry,
        )

        self.tokens_per_request = Histogram(
            "gateway_tokens_per_request",
            "Token usage per request",
            ["provider", "model", "token_type"],
            buckets=(10, 50, 100, 250, 500, 1000, 2000, 4000, 8000, 16000, 32000),
            registry=self.registry,
        )

        # Cost tracking
        self.cost_total = Counter(
            "gateway_cost_total_usd",
            "Total cost in USD",
            ["provider", "model"],
            registry=self.registry,
        )

        self.cost_per_request = Histogram(
            "gateway_cost_per_request_usd",
            "Cost per request in USD",
            ["provider", "model"],
            buckets=(
                0.0001,
                0.0005,
                0.001,
                0.005,
                0.01,
                0.05,
                0.1,
                0.5,
                1.0,
                5.0,
                10.0,
            ),
            registry=self.registry,
        )

        # Active requests
        self.active_requests = Gauge(
            "gateway_active_requests",
            "Number of requests currently being processed",
            ["provider"],
            registry=self.registry,
        )

        # Provider health
        self.provider_health = Gauge(
            "gateway_provider_health",
            "Provider health status (1=healthy, 0=unhealthy)",
            ["provider"],
            registry=self.registry,
        )

        self.provider_health_latency = Gauge(
            "gateway_provider_health_latency_seconds",
            "Provider health check latency in seconds",
            ["provider"],
            registry=self.registry,
        )

        # Rate limiting
        self.rate_limit_hits = Counter(
            "gateway_rate_limit_hits_total",
            "Number of rate limit hits",
            ["endpoint", "client_id"],
            registry=self.registry,
        )

        # Gateway info
        self.gateway_info = Info(
            "gateway_info",
            "Gateway version and configuration information",
            registry=self.registry,
        )

        # Session tracking
        self.unique_sessions = Gauge(
            "gateway_unique_sessions",
            "Number of unique sessions currently tracked",
            registry=self.registry,
        )

        # Request size tracking
        self.request_size_bytes = Histogram(
            "gateway_request_size_bytes",
            "Size of request payload in bytes",
            ["provider"],
            buckets=(100, 500, 1000, 5000, 10000, 50000, 100000, 500000),
            registry=self.registry,
        )

        self.response_size_bytes = Histogram(
            "gateway_response_size_bytes",
            "Size of response payload in bytes",
            ["provider"],
            buckets=(100, 500, 1000, 5000, 10000, 50000, 100000, 500000),
            registry=self.registry,
        )

    def record_request(
        self,
        provider: str,
        model: str,
        status: str = "success",
        latency_seconds: Optional[float] = None,
    ):
        """
        Record a completed request.

        Args:
            provider: Provider name
            model: Model identifier
            status: Request status (success, failed, rate_limited)
            latency_seconds: Request latency in seconds
        """
        self.requests_total.labels(provider=provider, model=model, status=status).inc()

        if status == "success":
            self.requests_success.labels(provider=provider, model=model).inc()

        if latency_seconds is not None:
            self.request_latency.labels(provider=provider, model=model).observe(
                latency_seconds
            )

    def record_failure(
        self, provider: str, model: str, error_type: str, latency_seconds: float
    ):
        """
        Record a failed request.

        Args:
            provider: Provider name
            model: Model identifier
            error_type: Type of error (api_error, timeout, validation, etc.)
            latency_seconds: Time until failure in seconds
        """
        self.requests_failed.labels(
            provider=provider, model=model, error_type=error_type
        ).inc()
        self.requests_total.labels(
            provider=provider, model=model, status="failed"
        ).inc()
        self.request_latency.labels(provider=provider, model=model).observe(
            latency_seconds
        )

    def record_fallback(
        self, from_provider: str, to_provider: str, success: bool = True
    ):
        """
        Record a fallback event.

        Args:
            from_provider: Original provider that failed
            to_provider: Fallback provider used
            success: Whether fallback was successful
        """
        self.fallback_triggered.labels(
            from_provider=from_provider, to_provider=to_provider
        ).inc()

        if success:
            self.fallback_success.labels(
                from_provider=from_provider, to_provider=to_provider
            ).inc()

    def record_provider_attempt(
        self, provider: str, model: str, attempt: int, latency_seconds: float
    ):
        """
        Record a provider-specific attempt (for fallback tracking).

        Args:
            provider: Provider name
            model: Model identifier
            attempt: Attempt number (1, 2, 3, etc.)
            latency_seconds: Attempt latency in seconds
        """
        self.provider_latency.labels(
            provider=provider, model=model, attempt=str(attempt)
        ).observe(latency_seconds)

    def record_tokens(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
    ):
        """
        Record token usage.

        Args:
            provider: Provider name
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            total_tokens: Total tokens (input + output)
        """
        self.tokens_consumed.labels(
            provider=provider, model=model, token_type="input"
        ).inc(input_tokens)
        self.tokens_consumed.labels(
            provider=provider, model=model, token_type="output"
        ).inc(output_tokens)
        self.tokens_consumed.labels(
            provider=provider, model=model, token_type="total"
        ).inc(total_tokens)

        self.tokens_per_request.labels(
            provider=provider, model=model, token_type="input"
        ).observe(input_tokens)
        self.tokens_per_request.labels(
            provider=provider, model=model, token_type="output"
        ).observe(output_tokens)
        self.tokens_per_request.labels(
            provider=provider, model=model, token_type="total"
        ).observe(total_tokens)

    def record_cost(self, provider: str, model: str, cost_usd: float):
        """
        Record request cost.

        Args:
            provider: Provider name
            model: Model identifier
            cost_usd: Cost in USD
        """
        self.cost_total.labels(provider=provider, model=model).inc(cost_usd)
        self.cost_per_request.labels(provider=provider, model=model).observe(cost_usd)

    def set_active_requests(self, provider: str, count: int):
        """
        Set number of active requests for a provider.

        Args:
            provider: Provider name
            count: Number of active requests
        """
        self.active_requests.labels(provider=provider).set(count)

    def increment_active_requests(self, provider: str):
        """Increment active request counter."""
        self.active_requests.labels(provider=provider).inc()

    def decrement_active_requests(self, provider: str):
        """Decrement active request counter."""
        self.active_requests.labels(provider=provider).dec()

    def record_provider_health(
        self, provider: str, is_healthy: bool, latency_seconds: float
    ):
        """
        Record provider health status.

        Args:
            provider: Provider name
            is_healthy: Health status
            latency_seconds: Health check latency
        """
        self.provider_health.labels(provider=provider).set(1 if is_healthy else 0)
        self.provider_health_latency.labels(provider=provider).set(latency_seconds)

    def record_rate_limit_hit(self, endpoint: str, client_id: str = "anonymous"):
        """
        Record a rate limit hit.

        Args:
            endpoint: Endpoint that was rate limited
            client_id: Client identifier
        """
        self.rate_limit_hits.labels(endpoint=endpoint, client_id=client_id).inc()

    def set_gateway_info(self, version: str, config: Dict[str, str]):
        """
        Set gateway information.

        Args:
            version: Gateway version
            config: Configuration details
        """
        info_dict = {"version": version, **config}
        self.gateway_info.info(info_dict)

    def set_unique_sessions(self, count: int):
        """
        Set number of unique sessions.

        Args:
            count: Number of unique sessions
        """
        self.unique_sessions.set(count)

    def record_request_size(self, provider: str, size_bytes: int):
        """
        Record request payload size.

        Args:
            provider: Provider name
            size_bytes: Size in bytes
        """
        self.request_size_bytes.labels(provider=provider).observe(size_bytes)

    def record_response_size(self, provider: str, size_bytes: int):
        """
        Record response payload size.

        Args:
            provider: Provider name
            size_bytes: Size in bytes
        """
        self.response_size_bytes.labels(provider=provider).observe(size_bytes)

    def get_metrics(self) -> bytes:
        """
        Get all metrics in Prometheus exposition format.

        Returns:
            Metrics in text format for Prometheus scraping
        """
        return generate_latest(self.registry)

    def get_stats(self) -> Dict[str, any]:
        """
        Get human-readable statistics summary.

        Returns:
            Dictionary with metric summaries
        """
        # This is a simplified version - in production you'd query the metrics
        return {
            "metrics_available": True,
            "registry": "prometheus",
            "endpoint": "/metrics",
            "description": "Prometheus-compatible metrics for scraping",
        }


# Global singleton instance
metrics_manager = MetricsManager()
