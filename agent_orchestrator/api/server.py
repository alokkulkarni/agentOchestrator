"""
FastAPI server for Agent Orchestrator.

Provides REST API endpoints with streaming support for real-time query updates.
"""

import logging
import os
import time
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, PlainTextResponse
from contextlib import asynccontextmanager

from ..orchestrator import Orchestrator
from ..observability import (
    orchestrator_metrics,
    get_correlation_id,
    set_correlation_id,
)
from .models import (
    QueryRequest,
    QueryResponse,
    HealthResponse,
    StatsResponse,
)
from .streaming import stream_query_progress

logger = logging.getLogger(__name__)

# Global orchestrator instance
orchestrator: Optional[Orchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI app."""
    global orchestrator

    # Startup
    logger.info("Starting Agent Orchestrator API...")

    # Get config path from environment or use default
    config_path = os.getenv("ORCHESTRATOR_CONFIG", "config/orchestrator.yaml")

    try:
        orchestrator = Orchestrator(config_path=config_path)
        await orchestrator.initialize()

        stats = orchestrator.get_stats()
        logger.info(
            f"✅ Orchestrator API started successfully - "
            f"{stats['agents']['total_agents']} agents registered"
        )
    except Exception as e:
        logger.error(f"❌ Failed to initialize orchestrator: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Agent Orchestrator API...")
    if orchestrator:
        await orchestrator.cleanup()
    logger.info("✅ Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Agent Orchestrator API",
    description="REST API for Agent Orchestrator with streaming support",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware for correlation ID
@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Add correlation ID to all requests."""
    # Get or generate correlation ID
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    set_correlation_id(correlation_id)

    # Process request
    response = await call_next(request)

    # Add correlation ID to response headers
    response.headers["X-Correlation-ID"] = correlation_id

    return response


def verify_api_key(authorization: Optional[str] = Header(None)):
    """Verify API key if authentication is enabled."""
    api_key_required = os.getenv("ORCHESTRATOR_REQUIRE_AUTH", "false").lower() == "true"

    if not api_key_required:
        return True

    expected_key = os.getenv("ORCHESTRATOR_API_KEY")
    if not expected_key:
        logger.warning("ORCHESTRATOR_REQUIRE_AUTH is true but ORCHESTRATOR_API_KEY not set")
        return True

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
        if token != expected_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return True
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header format")


@app.post("/v1/query")
async def query(
    request: QueryRequest,
    http_request: Request,
    authorization: Optional[str] = Header(None),
):
    """
    Process a query through the orchestrator with optional streaming.

    **Streaming Mode (default):**
    Returns Server-Sent Events (SSE) with real-time progress updates:
    - started: Query processing started
    - security_validation: Input validation status
    - reasoning_started: Agent selection in progress
    - reasoning_complete: Agents selected with confidence
    - agents_executing: Agents being called
    - validation: Response validation results
    - completed: Final result
    - error: If an error occurred

    **Non-Streaming Mode:**
    Set `stream: false` in request body to get a single JSON response.

    **Example (streaming with curl):**
    ```bash
    curl -N -X POST http://localhost:8001/v1/query \\
      -H "Content-Type: application/json" \\
      -d '{"query": "calculate 15 + 27", "stream": true}'
    ```

    **Example (non-streaming):**
    ```bash
    curl -X POST http://localhost:8001/v1/query \\
      -H "Content-Type: application/json" \\
      -d '{"query": "calculate 15 + 27", "stream": false}'
    ```
    """
    # Verify authentication
    verify_api_key(authorization)

    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    # Generate request ID
    request_id = str(uuid.uuid4())

    # Build request data
    request_data = {"query": request.query}

    # Add optional fields
    if request.operation:
        request_data["operation"] = request.operation
    if request.operands:
        request_data["operands"] = request.operands
    if request.data:
        request_data["data"] = request.data
    if request.filters:
        request_data["filters"] = request.filters
    if request.max_results:
        request_data["max_results"] = request.max_results
    if request.keywords:
        request_data["keywords"] = request.keywords
    if request.metadata:
        request_data.update(request.metadata)

    # Record metrics
    orchestrator_metrics.active_queries.inc()

    try:
        if request.stream:
            # Streaming response
            return StreamingResponse(
                stream_query_progress(
                    orchestrator=orchestrator,
                    request_data=request_data,
                    request_id=request_id,
                    session_id=request.session_id,
                    validate_input=request.validate_input,
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Request-ID": request_id,
                },
            )
        else:
            # Non-streaming response
            start_time = time.time()

            result = await orchestrator.process(
                request_data,
                validate_input_security=request.validate_input,
                request_id=request_id,
                session_id=request.session_id,
            )

            duration = time.time() - start_time

            # Record metrics
            orchestrator_metrics.queries_total.labels(
                status="success" if result.get("success") else "failed",
                reasoning_mode=orchestrator.config.reasoning_mode,
            ).inc()

            return QueryResponse(
                success=result.get("success", False),
                data=result.get("data", {}),
                request_id=request_id,
                session_id=request.session_id,
                metadata=result.get("_metadata", {}),
                errors=result.get("errors"),
            )

    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)

        # Record failure metric
        orchestrator_metrics.queries_failed.labels(
            reasoning_mode=orchestrator.config.reasoning_mode
        ).inc()

        raise HTTPException(status_code=500, detail=str(e))

    finally:
        orchestrator_metrics.active_queries.dec()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check health of orchestrator and all agents.

    Returns detailed health status including:
    - Overall orchestrator status
    - Individual agent health
    - Registered agent count
    - Available capabilities
    """
    if not orchestrator:
        return HealthResponse(
            status="unhealthy",
            orchestrator={"initialized": False, "error": "Orchestrator not initialized"},
            agents={},
            timestamp=time.time(),
        )

    try:
        stats = orchestrator.get_stats()

        # Check agent health
        agent_health = {}
        for agent_info in stats.get("agents", {}).get("agents", []):
            agent_health[agent_info["name"]] = {
                "healthy": agent_info.get("is_healthy", False),
                "call_count": agent_info.get("call_count", 0),
                "success_rate": agent_info.get("success_rate", 0),
            }

        # Overall status
        all_healthy = all(info["healthy"] for info in agent_health.values())
        status = "healthy" if all_healthy and orchestrator._initialized else "degraded"

        return HealthResponse(
            status=status,
            orchestrator={
                "name": stats["name"],
                "initialized": stats["initialized"],
                "request_count": stats["request_count"],
                "reasoning_mode": orchestrator.config.reasoning_mode,
            },
            agents={
                "total": len(agent_health),
                "healthy": sum(1 for info in agent_health.values() if info["healthy"]),
                "agents": agent_health,
                "capabilities": stats.get("agents", {}).get("capabilities", []),
            },
            timestamp=time.time(),
        )

    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        return HealthResponse(
            status="unhealthy",
            orchestrator={"error": str(e)},
            agents={},
            timestamp=time.time(),
        )


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """
    Get orchestrator statistics.

    Returns detailed statistics including:
    - Total requests processed
    - Agent statistics (calls, success rates, execution times)
    - Reasoning statistics
    - Cost tracking (if enabled)
    - Circuit breaker status
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        stats = orchestrator.get_stats()
        return StatsResponse(**stats)
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def metrics_endpoint():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus exposition format for scraping.
    Note: Metrics are also available on the dedicated metrics port (9090 by default).
    """
    try:
        from prometheus_client import generate_latest

        metrics = generate_latest(orchestrator_metrics.registry)
        return PlainTextResponse(content=metrics.decode("utf-8"))
    except Exception as e:
        logger.error(f"Error generating metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint with API information."""
    if not orchestrator:
        return {
            "service": "Agent Orchestrator API",
            "version": "1.0.0",
            "status": "initializing",
            "error": "Orchestrator not initialized",
        }

    stats = orchestrator.get_stats()

    return {
        "service": "Agent Orchestrator API",
        "version": "1.0.0",
        "status": "running",
        "orchestrator": {
            "name": stats["name"],
            "reasoning_mode": orchestrator.config.reasoning_mode,
            "agents": stats["agents"]["total_agents"],
            "capabilities": stats["agents"]["capabilities"],
        },
        "endpoints": {
            "query": "POST /v1/query - Process queries (supports streaming)",
            "health": "GET /health - Health check",
            "stats": "GET /stats - Statistics",
            "metrics": "GET /metrics - Prometheus metrics",
            "docs": "GET /docs - Interactive API documentation",
        },
        "features": {
            "streaming": "Server-Sent Events (SSE) for real-time updates",
            "observability": "Full metrics, tracing, and logging",
            "authentication": os.getenv("ORCHESTRATOR_REQUIRE_AUTH", "false") == "true",
        },
    }


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc),
            "request_id": get_correlation_id(),
        },
    )


if __name__ == "__main__":
    import uvicorn

    # Get configuration from environment
    host = os.getenv("ORCHESTRATOR_API_HOST", "0.0.0.0")
    port = int(os.getenv("ORCHESTRATOR_API_PORT", "8001"))
    reload = os.getenv("ORCHESTRATOR_API_RELOAD", "false").lower() == "true"
    log_level = os.getenv("ORCHESTRATOR_API_LOG_LEVEL", "info").lower()

    uvicorn.run(
        "agent_orchestrator.api.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )
