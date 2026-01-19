"""
Model Gateway FastAPI server.

Provides unified API for accessing multiple AI providers.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import load_gateway_config, load_settings
from .providers import AnthropicProvider, BedrockProvider

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Model Gateway",
    description="Unified API for accessing multiple AI model providers",
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

# Global state
gateway_config = None
settings = None
providers = {}


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


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    providers: Dict[str, Any]
    timestamp: float


@app.on_event("startup")
async def startup_event():
    """Initialize gateway on startup."""
    global gateway_config, settings, providers

    logger.info("Starting Model Gateway...")

    # Load configuration
    settings = load_settings()
    gateway_config = load_gateway_config()

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
    authorization: Optional[str] = Header(None),
):
    """
    Generate text using specified provider and model with automatic fallback.

    If the requested provider fails and fallback is enabled, automatically tries
    alternative providers transparently. All fallback events are logged.

    Args:
        request: Generation request with messages and parameters
        authorization: Optional Bearer token for authentication

    Returns:
        Generated response with content and metadata
    """
    # Verify authentication
    verify_api_key(authorization)

    start_time = time.time()

    # Determine provider order for fallback
    requested_provider = request.provider or gateway_config.default_provider

    # Build list of providers to try
    providers_to_try = []

    if gateway_config.fallback.enabled:
        # Start with requested provider
        providers_to_try.append(requested_provider)

        # Add fallback providers from config (skip if already added)
        for fallback_provider in gateway_config.fallback.fallback_order:
            if fallback_provider not in providers_to_try and fallback_provider in providers:
                providers_to_try.append(fallback_provider)

        # Limit to max fallback attempts
        providers_to_try = providers_to_try[:gateway_config.fallback.max_fallback_attempts]
    else:
        # No fallback - only try requested provider
        providers_to_try = [requested_provider]

    # Convert messages to dict format
    messages = [msg.model_dump() for msg in request.messages]

    last_error = None
    attempts_log = []

    # Try each provider in order
    for attempt_num, provider_name in enumerate(providers_to_try, 1):
        if provider_name not in providers:
            logger.warning(f"Provider '{provider_name}' not available, skipping")
            continue

        provider = providers[provider_name]
        attempt_start = time.time()

        try:
            # Generate response
            response = await provider.generate(
                messages=messages,
                model=request.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )

            attempt_latency_ms = (time.time() - attempt_start) * 1000
            total_latency_ms = (time.time() - start_time) * 1000

            # Log success
            if attempt_num > 1:
                # This was a fallback - log the transition
                logger.warning(
                    f"🔄 FALLBACK SUCCESS: Provider '{provider_name}' succeeded after '{requested_provider}' failed. "
                    f"Attempt {attempt_num}/{len(providers_to_try)}, "
                    f"latency={attempt_latency_ms:.2f}ms"
                )

            if settings.log_requests:
                logger.info(
                    f"Generated response: provider={provider_name}, "
                    f"model={response['model']}, "
                    f"tokens={response['usage']['total_tokens']}, "
                    f"latency={total_latency_ms:.2f}ms"
                    + (f" (fallback from {requested_provider})" if attempt_num > 1 else "")
                )

            return GenerateResponse(
                content=response["content"],
                model=response["model"],
                provider=response["provider"],
                usage=response["usage"],
                finish_reason=response["finish_reason"],
                latency_ms=round(total_latency_ms, 2),
            )

        except Exception as e:
            attempt_latency_ms = (time.time() - attempt_start) * 1000
            last_error = e

            # Log the failure
            error_msg = str(e)[:200]  # Truncate long errors
            attempts_log.append({
                "provider": provider_name,
                "attempt": attempt_num,
                "error": error_msg,
                "latency_ms": round(attempt_latency_ms, 2)
            })

            if attempt_num < len(providers_to_try):
                # More providers to try - log as warning
                logger.warning(
                    f"⚠️  Provider '{provider_name}' failed (attempt {attempt_num}/{len(providers_to_try)}): {error_msg}. "
                    f"Trying fallback to '{providers_to_try[attempt_num]}'..."
                )
            else:
                # Last provider failed - log as error
                logger.error(
                    f"❌ All providers failed after {attempt_num} attempt(s). "
                    f"Last error from '{provider_name}': {error_msg}"
                )

    # All providers failed
    total_latency_ms = (time.time() - start_time) * 1000

    error_detail = {
        "message": "All providers failed",
        "requested_provider": requested_provider,
        "attempts": attempts_log,
        "total_latency_ms": round(total_latency_ms, 2),
        "last_error": str(last_error)
    }

    logger.error(f"Request failed: {error_detail}")
    raise HTTPException(status_code=500, detail=error_detail)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check health of gateway and all providers.

    Returns:
        Health status for gateway and each provider
    """
    provider_health = {}

    for name, provider in providers.items():
        try:
            health = await provider.health_check()
            provider_health[name] = health
        except Exception as e:
            provider_health[name] = {
                "status": "unhealthy",
                "error": str(e),
            }

    # Overall status is healthy if at least one provider is healthy
    overall_status = "healthy" if any(
        p.get("status") == "healthy" for p in provider_health.values()
    ) else "unhealthy"

    return HealthResponse(
        status=overall_status,
        providers=provider_health,
        timestamp=time.time(),
    )


@app.get("/providers")
async def list_providers():
    """
    List available providers and their models.

    Returns:
        Dict of provider information
    """
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
    }


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
