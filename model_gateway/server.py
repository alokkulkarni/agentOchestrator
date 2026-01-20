"""
Model Gateway FastAPI server with comprehensive observability.

Provides unified API for accessing multiple AI providers with:
- Distributed tracing (OpenTelemetry)
- Metrics collection (Prometheus)
- Structured JSON logging
- PII sanitization
- Cost tracking
- Rate limiting
- Session and correlation ID tracking
"""

import logging
import os
import time
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Load environment variables from .env file
from dotenv import load_dotenv

# Load .env from project root (parent of model_gateway/)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=False)  # Don't override existing env vars

from fastapi import FastAPI, HTTPException, Header, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
from slowapi.errors import RateLimitExceeded

from .config import load_gateway_config, load_settings
from .providers import AnthropicProvider, BedrockProvider

# Import observability modules
from .observability import (
    metrics_manager,
    init_tracing,
    get_tracer,
    setup_structured_logging,
    sanitize_content,
    cost_tracker,
    init_rate_limiting,
)
from .observability.middleware import (
    CorrelationIDMiddleware,
    SessionTrackingMiddleware,
    RequestLoggingMiddleware,
    MetricsMiddleware,
    get_correlation_id,
)
from .observability.logging_config import get_structured_logger
from .observability.tracing import TracingContext, add_span_attributes, record_exception

# Initialize observability
logger = get_structured_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Model Gateway",
    description="Unified API for accessing multiple AI model providers with observability",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add observability middleware (must be added before app starts)
app.add_middleware(CorrelationIDMiddleware, generate_if_missing=True)
app.add_middleware(SessionTrackingMiddleware, generate_if_missing=True)
app.add_middleware(RequestLoggingMiddleware, sanitize_logs=True)
app.add_middleware(MetricsMiddleware)

# Global state
gateway_config = None
settings = None
providers = {}
session_tracking_middleware = None


# Request/Response models
class Message(BaseModel):
    """Message format."""

    role: str = Field(..., description="Role: user, assistant, or system")
    content: str = Field(..., description="Message content")


class GenerateRequest(BaseModel):
    """Request format for /v1/generate endpoint."""

    messages: List[Message] = Field(..., description="List of messages")
    provider: Optional[str] = Field(
        default=None, description="Provider name (anthropic, bedrock)"
    )
    model: Optional[str] = Field(default=None, description="Model identifier")
    max_tokens: int = Field(default=4096, description="Maximum tokens to generate")
    temperature: float = Field(default=0.0, description="Sampling temperature")


class GenerateResponse(BaseModel):
    """Response format for /v1/generate endpoint."""

    content: str = Field(..., description="Generated text")
    model: str = Field(..., description="Model used")
    provider: str = Field(..., description="Provider used")
    usage: Dict[str, int] = Field(..., description="Token usage")
    finish_reason: str = Field(..., description="Completion reason")
    latency_ms: float = Field(..., description="Request latency in milliseconds")
    cost_usd: Optional[float] = Field(None, description="Estimated cost in USD")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    providers: Dict[str, Any]
    timestamp: float


@app.on_event("startup")
async def startup_event():
    """Initialize gateway on startup with observability."""
    global gateway_config, settings, providers, session_tracking_middleware

    logger.info("Starting Model Gateway with observability features...")

    # Load configuration
    settings = load_settings()
    gateway_config = load_gateway_config()

    # Setup structured logging
    log_file = "model_gateway/logs/gateway.log" if settings.log_requests else None
    setup_structured_logging(
        log_level=settings.log_level,
        log_file=log_file,
        enable_console=True,
        json_format=True,
        enable_rotation=True,
        sanitize_logs=True,
        include_trace_info=True,
    )

    # Initialize tracing (OTLP endpoint can be configured via env)
    import os

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    enable_console_trace = os.getenv("OTEL_CONSOLE", "false").lower() == "true"

    try:
        init_tracing(
            service_name="model-gateway",
            service_version="1.0.0",
            otlp_endpoint=otlp_endpoint,
            enable_console=enable_console_trace,
        )
        logger.info("✅ OpenTelemetry tracing initialized", otlp_endpoint=otlp_endpoint)
    except Exception as e:
        logger.warning("⚠️  Tracing initialization failed", error=str(e))

    # Initialize rate limiting
    rate_limit_enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    rate_limit_default = os.getenv("RATE_LIMIT_DEFAULT", "100/minute")

    rate_limiter = init_rate_limiting(
        default_limits=rate_limit_default, enabled=rate_limit_enabled
    )
    logger.info(
        "✅ Rate limiting initialized", enabled=rate_limit_enabled, limits=rate_limit_default
    )

    # Set gateway info for metrics
    metrics_manager.set_gateway_info(
        version="1.0.0",
        config={
            "providers": str(len(gateway_config.providers)),
            "fallback_enabled": str(gateway_config.fallback.enabled),
        },
    )

    logger.info(f"Loaded configuration with {len(gateway_config.providers)} providers")

    # Initialize providers
    for name, provider_config in gateway_config.providers.items():
        if not provider_config.enabled:
            logger.info(f"Provider '{name}' is disabled, skipping")
            continue

        try:
            if provider_config.type == "anthropic":
                providers[name] = AnthropicProvider(provider_config.model_dump())
                logger.info(f"✅ Initialized Anthropic provider: {name}")
            elif provider_config.type == "bedrock":
                providers[name] = BedrockProvider(provider_config.model_dump())
                logger.info(f"✅ Initialized Bedrock provider: {name}")
            else:
                logger.warning(f"Unknown provider type: {provider_config.type}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize provider '{name}': {e}")

    if not providers:
        logger.error("No providers initialized! Check your configuration.")
    else:
        logger.info(f"Gateway started with {len(providers)} provider(s)")

    logger.info("🚀 Model Gateway startup complete with full observability")


def verify_api_key(authorization: Optional[str] = Header(None)):
    """Verify API key if authentication is required."""
    if not settings.require_auth:
        return True

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    # Expected format: "Bearer <api_key>"
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
        if token != settings.api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return True
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header format")


@app.post("/v1/generate", response_model=GenerateResponse)
async def generate(
    request: GenerateRequest,
    http_request: Request,
    authorization: Optional[str] = Header(None),
):
    """
    Generate text using specified provider and model with automatic fallback.

    Includes full observability:
    - Distributed tracing
    - Metrics collection
    - Cost tracking
    - PII sanitization in logs
    - Correlation ID tracking
    """
    # Verify authentication
    verify_api_key(authorization)

    start_time = time.time()
    correlation_id = get_correlation_id()

    # Create trace span
    with TracingContext(
        "generate_request",
        {
            "provider": request.provider or gateway_config.default_provider,
            "model": request.model or "default",
            "max_tokens": request.max_tokens,
            "correlation_id": correlation_id,
        },
    ) as span:
        # Determine provider order for fallback
        requested_provider = request.provider or gateway_config.default_provider

        # Build list of providers to try
        providers_to_try = []

        if gateway_config.fallback.enabled:
            providers_to_try.append(requested_provider)
            for fallback_provider in gateway_config.fallback.fallback_order:
                if (
                    fallback_provider not in providers_to_try
                    and fallback_provider in providers
                ):
                    providers_to_try.append(fallback_provider)
            providers_to_try = providers_to_try[
                : gateway_config.fallback.max_fallback_attempts
            ]
        else:
            providers_to_try = [requested_provider]

        # Convert messages to dict format (with sanitization for logs)
        messages = [msg.model_dump() for msg in request.messages]
        sanitized_messages = sanitize_content(messages, sanitize_text_content=False)

        last_error = None
        attempts_log = []

        # Try each provider in order
        for attempt_num, provider_name in enumerate(providers_to_try, 1):
            if provider_name not in providers:
                logger.warning(f"Provider '{provider_name}' not available, skipping")
                continue

            provider = providers[provider_name]
            attempt_start = time.time()

            # Increment active requests metric
            metrics_manager.increment_active_requests(provider_name)

            try:
                # Create span for provider attempt
                with TracingContext(
                    f"provider_attempt_{attempt_num}",
                    {
                        "provider": provider_name,
                        "attempt": attempt_num,
                        "model": request.model or "default",
                    },
                ) as provider_span:
                    # Generate response
                    response = await provider.generate(
                        messages=messages,
                        model=request.model,
                        max_tokens=request.max_tokens,
                        temperature=request.temperature,
                    )

                    attempt_latency_ms = (time.time() - attempt_start) * 1000
                    total_latency_ms = (time.time() - start_time) * 1000

                    # Track cost
                    cost_info = cost_tracker.track_request_cost(
                        model=response["model"],
                        input_tokens=response["usage"]["input_tokens"],
                        output_tokens=response["usage"]["output_tokens"],
                        provider=provider_name,
                    )

                    # Record metrics
                    metrics_manager.record_request(
                        provider=provider_name,
                        model=response["model"],
                        status="success",
                        latency_seconds=total_latency_ms / 1000,
                    )

                    metrics_manager.record_provider_attempt(
                        provider=provider_name,
                        model=response["model"],
                        attempt=attempt_num,
                        latency_seconds=attempt_latency_ms / 1000,
                    )

                    metrics_manager.record_tokens(
                        provider=provider_name,
                        model=response["model"],
                        input_tokens=response["usage"]["input_tokens"],
                        output_tokens=response["usage"]["output_tokens"],
                        total_tokens=response["usage"]["total_tokens"],
                    )

                    metrics_manager.record_cost(
                        provider=provider_name,
                        model=response["model"],
                        cost_usd=cost_info["cost_usd"],
                    )

                    # Record fallback success if this was not first attempt
                    if attempt_num > 1:
                        metrics_manager.record_fallback(
                            from_provider=requested_provider,
                            to_provider=provider_name,
                            success=True,
                        )

                        logger.warning(
                            "fallback_success",
                            from_provider=requested_provider,
                            to_provider=provider_name,
                            attempt=attempt_num,
                            latency_ms=round(attempt_latency_ms, 2),
                            correlation_id=correlation_id,
                        )

                    # Log success
                    if settings.log_requests:
                        logger.info(
                            "generation_success",
                            provider=provider_name,
                            model=response["model"],
                            input_tokens=response["usage"]["input_tokens"],
                            output_tokens=response["usage"]["output_tokens"],
                            total_tokens=response["usage"]["total_tokens"],
                            cost_usd=cost_info["cost_usd"],
                            latency_ms=round(total_latency_ms, 2),
                            correlation_id=correlation_id,
                            fallback=attempt_num > 1,
                        )

                    # Decrement active requests
                    metrics_manager.decrement_active_requests(provider_name)

                    return GenerateResponse(
                        content=response["content"],
                        model=response["model"],
                        provider=response["provider"],
                        usage=response["usage"],
                        finish_reason=response["finish_reason"],
                        latency_ms=round(total_latency_ms, 2),
                        cost_usd=round(cost_info["cost_usd"], 6),
                        correlation_id=correlation_id,
                    )

            except Exception as e:
                attempt_latency_ms = (time.time() - attempt_start) * 1000
                last_error = e

                # Decrement active requests
                metrics_manager.decrement_active_requests(provider_name)

                # Log the failure
                error_msg = str(e)[:200]  # Truncate long errors
                attempts_log.append(
                    {
                        "provider": provider_name,
                        "attempt": attempt_num,
                        "error": error_msg,
                        "latency_ms": round(attempt_latency_ms, 2),
                    }
                )

                # Record metrics
                error_type = type(e).__name__
                metrics_manager.record_failure(
                    provider=provider_name,
                    model=request.model or "unknown",
                    error_type=error_type,
                    latency_seconds=attempt_latency_ms / 1000,
                )

                # Record fallback trigger
                if attempt_num < len(providers_to_try):
                    next_provider = providers_to_try[attempt_num]
                    metrics_manager.record_fallback(
                        from_provider=provider_name,
                        to_provider=next_provider,
                        success=False,
                    )

                    logger.warning(
                        "provider_failed_fallback",
                        provider=provider_name,
                        attempt=attempt_num,
                        total_attempts=len(providers_to_try),
                        error=error_msg,
                        next_provider=next_provider,
                        correlation_id=correlation_id,
                    )
                else:
                    logger.error(
                        "all_providers_failed",
                        provider=provider_name,
                        attempts=attempt_num,
                        error=error_msg,
                        correlation_id=correlation_id,
                    )

                # Record exception in span
                record_exception(span, e)

        # All providers failed
        total_latency_ms = (time.time() - start_time) * 1000

        error_detail = {
            "message": "All providers failed",
            "requested_provider": requested_provider,
            "attempts": attempts_log,
            "total_latency_ms": round(total_latency_ms, 2),
            "last_error": str(last_error),
            "correlation_id": correlation_id,
        }

        logger.error("request_failed_all_providers", **error_detail)
        raise HTTPException(status_code=500, detail=error_detail)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check health of gateway and all providers.
    """
    with TracingContext("health_check"):
        provider_health = {}

        for name, provider in providers.items():
            try:
                start_time = time.time()
                health = await provider.health_check()
                latency_seconds = time.time() - start_time

                provider_health[name] = health

                # Record health metrics
                is_healthy = health.get("status") == "healthy"
                metrics_manager.record_provider_health(
                    provider=name, is_healthy=is_healthy, latency_seconds=latency_seconds
                )

            except Exception as e:
                provider_health[name] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
                metrics_manager.record_provider_health(
                    provider=name, is_healthy=False, latency_seconds=0
                )

        # Overall status is healthy if at least one provider is healthy
        overall_status = (
            "healthy"
            if any(p.get("status") == "healthy" for p in provider_health.values())
            else "unhealthy"
        )

        return HealthResponse(
            status=overall_status,
            providers=provider_health,
            timestamp=time.time(),
        )


@app.get("/metrics")
async def metrics_endpoint():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus exposition format for scraping.
    """
    metrics = metrics_manager.get_metrics()
    return PlainTextResponse(content=metrics.decode("utf-8"))


@app.get("/metrics/stats")
async def metrics_stats():
    """
    Get human-readable metrics statistics.
    """
    cost_stats = cost_tracker.get_statistics()
    active_sessions = (
        session_tracking_middleware.get_active_session_count()
        if session_tracking_middleware
        else 0
    )

    metrics_manager.set_unique_sessions(active_sessions)

    return {
        "cost_tracking": cost_stats,
        "active_sessions": active_sessions,
        "metrics_endpoint": "/metrics",
    }


@app.get("/providers")
async def list_providers():
    """
    List available providers and their models.
    """
    with TracingContext("list_providers"):
        provider_info = {}

        for name, provider in providers.items():
            try:
                info = provider.get_model_info()
                provider_info[name] = info
            except Exception as e:
                provider_info[name] = {"error": str(e)}

        return provider_info


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Model Gateway",
        "version": "1.0.0",
        "status": "running",
        "providers": list(providers.keys()),
        "observability": {
            "metrics": "/metrics",
            "metrics_stats": "/metrics/stats",
            "health": "/health",
            "tracing": "OpenTelemetry enabled",
            "logging": "Structured JSON logging enabled",
        },
    }


# Error handlers
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors."""
    correlation_id = get_correlation_id()

    logger.warning(
        "rate_limit_exceeded",
        path=request.url.path,
        correlation_id=correlation_id,
    )

    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded",
            "correlation_id": correlation_id,
        },
        headers={"Retry-After": "60"},
    )


if __name__ == "__main__":
    import uvicorn

    settings = load_settings()
    uvicorn.run(
        "model_gateway.server:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )
