"""
Prometheus metrics for Agent Orchestrator.

Tracks:
- Query processing metrics
- Reasoning engine performance
- Agent execution metrics
- Validation results
- Retry attempts
- Session tracking
"""

from typing import Dict, Optional
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    CollectorRegistry,
    generate_latest,
)


class OrchestratorMetrics:
    """Manages all Prometheus metrics for the orchestrator."""

    def __init__(self):
        """Initialize metrics manager with all metric collectors."""
        self.registry = CollectorRegistry()

        # Query metrics
        self.queries_total = Counter(
            "orchestrator_queries_total",
            "Total number of queries processed",
            ["status", "reasoning_mode"],
            registry=self.registry,
        )

        self.queries_success = Counter(
            "orchestrator_queries_success_total",
            "Total successful queries",
            ["reasoning_mode"],
            registry=self.registry,
        )

        self.queries_failed = Counter(
            "orchestrator_queries_failed_total",
            "Total failed queries",
            ["error_type", "reasoning_mode"],
            registry=self.registry,
        )

        # Query latency (with percentile buckets)
        self.query_duration = Histogram(
            "orchestrator_query_duration_seconds",
            "Query processing duration",
            ["reasoning_mode"],
            buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 15.0, 30.0, 60.0),
            registry=self.registry,
        )

        # Reasoning metrics
        self.reasoning_decisions = Counter(
            "orchestrator_reasoning_decisions_total",
            "Total reasoning decisions",
            ["method", "reasoning_mode"],  # method: rule/ai/hybrid
            registry=self.registry,
        )

        self.reasoning_confidence = Histogram(
            "orchestrator_reasoning_confidence",
            "Reasoning confidence scores",
            ["method"],
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0),
            registry=self.registry,
        )

        self.reasoning_duration = Histogram(
            "orchestrator_reasoning_duration_seconds",
            "Reasoning engine duration",
            ["method"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
            registry=self.registry,
        )

        # Agent metrics
        self.agent_calls_total = Counter(
            "orchestrator_agent_calls_total",
            "Total agent calls",
            ["agent_name", "status"],
            registry=self.registry,
        )

        self.agent_duration = Histogram(
            "orchestrator_agent_duration_seconds",
            "Agent execution duration",
            ["agent_name"],
            buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
            registry=self.registry,
        )

        self.agent_retries = Counter(
            "orchestrator_agent_retries_total",
            "Agent retry attempts",
            ["agent_name", "reason"],
            registry=self.registry,
        )

        self.agent_fallbacks = Counter(
            "orchestrator_agent_fallbacks_total",
            "Agent fallback invocations",
            ["from_agent", "to_agent"],
            registry=self.registry,
        )

        # Validation metrics
        self.validation_checks = Counter(
            "orchestrator_validation_checks_total",
            "Total validation checks",
            ["result"],  # valid/invalid
            registry=self.registry,
        )

        self.validation_confidence = Histogram(
            "orchestrator_validation_confidence",
            "Validation confidence scores",
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0),
            registry=self.registry,
        )

        self.hallucination_detected = Counter(
            "orchestrator_hallucination_detected_total",
            "Hallucinations detected in responses",
            ["agent_name"],
            registry=self.registry,
        )

        self.validation_retries = Counter(
            "orchestrator_validation_retries_total",
            "Retries due to validation failure",
            ["reason"],
            registry=self.registry,
        )

        # Cost metrics
        self.ai_reasoner_cost = Counter(
            "orchestrator_ai_reasoner_cost_usd",
            "AI reasoner API cost in USD",
            ["provider", "model"],
            registry=self.registry,
        )

        self.ai_reasoner_tokens = Counter(
            "orchestrator_ai_reasoner_tokens_total",
            "AI reasoner token usage",
            ["provider", "model", "token_type"],  # input/output
            registry=self.registry,
        )

        # Session metrics
        self.unique_sessions = Gauge(
            "orchestrator_unique_sessions",
            "Number of unique active sessions",
            registry=self.registry,
        )

        self.queries_per_session = Histogram(
            "orchestrator_queries_per_session",
            "Queries per session distribution",
            buckets=(1, 2, 3, 5, 10, 20, 50, 100),
            registry=self.registry,
        )

        # System metrics
        self.active_queries = Gauge(
            "orchestrator_active_queries",
            "Currently processing queries",
            registry=self.registry,
        )

        self.registered_agents = Gauge(
            "orchestrator_registered_agents",
            "Number of registered agents",
            registry=self.registry,
        )

        self.circuit_breaker_open = Gauge(
            "orchestrator_circuit_breaker_open",
            "Circuit breaker status (1=open, 0=closed)",
            ["agent_name"],
            registry=self.registry,
        )

        # Info metric
        self.orchestrator_info = Info(
            "orchestrator_info",
            "Orchestrator version and configuration",
            registry=self.registry,
        )

    # Query metrics methods
    def record_query(
        self,
        success: bool,
        reasoning_mode: str,
        duration_seconds: float,
        error_type: Optional[str] = None,
    ):
        """Record a completed query."""
        status = "success" if success else "failed"
        self.queries_total.labels(status=status, reasoning_mode=reasoning_mode).inc()

        if success:
            self.queries_success.labels(reasoning_mode=reasoning_mode).inc()
        else:
            self.queries_failed.labels(
                error_type=error_type or "unknown", reasoning_mode=reasoning_mode
            ).inc()

        self.query_duration.labels(reasoning_mode=reasoning_mode).observe(
            duration_seconds
        )

    def increment_active_queries(self):
        """Increment active query counter."""
        self.active_queries.inc()

    def decrement_active_queries(self):
        """Decrement active query counter."""
        self.active_queries.dec()

    # Reasoning metrics methods
    def record_reasoning(
        self,
        method: str,  # rule/ai/hybrid
        reasoning_mode: str,
        confidence: float,
        duration_seconds: float,
    ):
        """Record a reasoning decision."""
        self.reasoning_decisions.labels(
            method=method, reasoning_mode=reasoning_mode
        ).inc()
        self.reasoning_confidence.labels(method=method).observe(confidence)
        self.reasoning_duration.labels(method=method).observe(duration_seconds)

    # Agent metrics methods
    def record_agent_call(
        self, agent_name: str, success: bool, duration_seconds: float
    ):
        """Record an agent call."""
        status = "success" if success else "failed"
        self.agent_calls_total.labels(agent_name=agent_name, status=status).inc()
        self.agent_duration.labels(agent_name=agent_name).observe(duration_seconds)

    def record_agent_retry(self, agent_name: str, reason: str):
        """Record an agent retry."""
        self.agent_retries.labels(agent_name=agent_name, reason=reason).inc()

    def record_agent_fallback(self, from_agent: str, to_agent: str):
        """Record an agent fallback."""
        self.agent_fallbacks.labels(from_agent=from_agent, to_agent=to_agent).inc()

    # Validation metrics methods
    def record_validation(self, is_valid: bool, confidence: float):
        """Record a validation check."""
        result = "valid" if is_valid else "invalid"
        self.validation_checks.labels(result=result).inc()
        self.validation_confidence.observe(confidence)

    def record_hallucination(self, agent_name: str):
        """Record a detected hallucination."""
        self.hallucination_detected.labels(agent_name=agent_name).inc()

    def record_validation_retry(self, reason: str):
        """Record a validation retry."""
        self.validation_retries.labels(reason=reason).inc()

    # Cost metrics methods
    def record_ai_cost(
        self,
        provider: str,
        model: str,
        cost_usd: float,
        input_tokens: int,
        output_tokens: int,
    ):
        """Record AI reasoner cost and token usage."""
        self.ai_reasoner_cost.labels(provider=provider, model=model).inc(cost_usd)
        self.ai_reasoner_tokens.labels(
            provider=provider, model=model, token_type="input"
        ).inc(input_tokens)
        self.ai_reasoner_tokens.labels(
            provider=provider, model=model, token_type="output"
        ).inc(output_tokens)

    # Session metrics methods
    def set_unique_sessions(self, count: int):
        """Set number of unique sessions."""
        self.unique_sessions.set(count)

    def record_session_queries(self, count: int):
        """Record queries per session."""
        self.queries_per_session.observe(count)

    # System metrics methods
    def set_registered_agents(self, count: int):
        """Set number of registered agents."""
        self.registered_agents.set(count)

    def set_circuit_breaker(self, agent_name: str, is_open: bool):
        """Set circuit breaker status."""
        self.circuit_breaker_open.labels(agent_name=agent_name).set(1 if is_open else 0)

    def set_orchestrator_info(self, version: str, config: Dict[str, str]):
        """Set orchestrator information."""
        info_dict = {"version": version, **config}
        self.orchestrator_info.info(info_dict)

    # Export methods
    def get_metrics(self) -> bytes:
        """Get metrics in Prometheus exposition format."""
        return generate_latest(self.registry)

    def get_stats(self) -> Dict[str, any]:
        """Get human-readable statistics summary."""
        return {
            "metrics_available": True,
            "registry": "prometheus",
            "description": "Orchestrator metrics for Prometheus scraping",
        }


# Global singleton
orchestrator_metrics = OrchestratorMetrics()
