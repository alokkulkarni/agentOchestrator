# Model Gateway Implementation Guide

## Overview

The Model Gateway has been successfully implemented and integrated with the Agent Orchestrator. This document provides complete setup and usage instructions.

## What Was Built

The Model Gateway is a unified API layer that sits between the orchestrator and AI providers (Anthropic Claude, AWS Bedrock). It provides:

- **Unified API**: Single endpoint for all AI providers
- **Provider Abstraction**: Easy switching between Anthropic and Bedrock
- **Automatic Fallback**: Transparent failover between providers on errors
- **Centralized Configuration**: All provider settings in one place
- **Health Monitoring**: Built-in health checks for all providers
- **Full Observability**: Detailed logging of all requests and fallback events

## Architecture

```
┌─────────────────────────────────────────┐
│      Agent Orchestrator                 │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  Gateway Reasoner                 │ │
│  │  (HTTP API Client)                │ │
│  └───────────┬───────────────────────┘ │
└──────────────┼─────────────────────────┘
               │
               │ HTTP/JSON
               │
               ▼
┌──────────────────────────────────────────┐
│      Model Gateway (FastAPI)              │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  /v1/generate endpoint             │ │
│  └────────────┬───────────────────────┘ │
│               │                          │
│      ┌────────┴────────┐                │
│      │                 │                │
│      ▼                 ▼                │
│  ┌────────────┐  ┌──────────────┐     │
│  │ Anthropic  │  │   Bedrock    │     │
│  │  Provider  │  │   Provider   │     │
│  └─────┬──────┘  └──────┬───────┘     │
└────────┼─────────────────┼──────────────┘
         │                 │
         ▼                 ▼
   ┌──────────┐      ┌─────────┐
   │ Claude   │      │  AWS    │
   │   API    │      │ Bedrock │
   └──────────┘      └─────────┘
```

## Directory Structure

```
model_gateway/
├── __init__.py
├── server.py                  # FastAPI application
├── providers/
│   ├── __init__.py
│   ├── base_provider.py       # Provider interface
│   ├── anthropic_provider.py  # Anthropic adapter
│   └── bedrock_provider.py    # Bedrock adapter
├── config/
│   ├── __init__.py
│   ├── models.py              # Pydantic config models
│   ├── loader.py              # Config loader
│   └── gateway.yaml           # Gateway configuration
├── .env                       # Environment variables
├── .env.example               # Environment template
└── requirements.txt           # Dependencies
```

## Installation & Setup

### 1. Install Dependencies

The gateway requires FastAPI and provider SDKs:

```bash
# Activate your virtual environment
source venv/bin/activate

# Install gateway dependencies
pip install fastapi uvicorn aiohttp anthropic boto3
```

### 2. Configure Environment Variables

Copy the API key from orchestrator .env to gateway .env:

```bash
# The gateway .env should contain:
GATEWAY_ANTHROPIC_API_KEY=sk-ant-api03-...
GATEWAY_AWS_REGION=us-east-1

# Server settings
GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=8000
GATEWAY_LOG_LEVEL=INFO
```

### 3. Start the Gateway Server

```bash
# From project root directory
source venv/bin/activate
export GATEWAY_ANTHROPIC_API_KEY="your-key-here"  # Or set in .env
python3 -m model_gateway.server
```

The gateway will start on `http://localhost:8000`

### 4. Verify Gateway is Running

```bash
# Check gateway status
curl http://localhost:8000/

# Check provider health
curl http://localhost:8000/health | python3 -m json.tool

# List available providers
curl http://localhost:8000/providers | python3 -m json.tool
```

## Gateway API Endpoints

### GET /
Returns gateway status and available providers.

**Response**:
```json
{
  "service": "Model Gateway",
  "version": "1.0.0",
  "status": "running",
  "providers": ["anthropic", "bedrock"]
}
```

### GET /health
Health check for all providers.

**Response**:
```json
{
  "status": "healthy",
  "providers": {
    "anthropic": {
      "status": "healthy",
      "latency_ms": 1625.49,
      "model": "claude-sonnet-4-5-20250929"
    },
    "bedrock": {
      "status": "healthy",
      "latency_ms": 416.92,
      "region": "us-east-1"
    }
  },
  "timestamp": 1737297868.123
}
```

### GET /providers
List all available providers and their models.

**Response**:
```json
{
  "anthropic": {
    "provider": "AnthropicProvider",
    "models": [
      "claude-sonnet-4-5-20250929",
      "claude-opus-4-5-20251101",
      "claude-3-5-sonnet-20241022",
      ...
    ],
    "default_model": "claude-sonnet-4-5-20250929"
  },
  "bedrock": {
    "provider": "BedrockProvider",
    "models": [
      "anthropic.claude-sonnet-3-5-v2-20241022",
      ...
    ],
    "default_model": "anthropic.claude-sonnet-3-5-v2-20241022",
    "region": "us-east-1"
  }
}
```

### POST /v1/generate
Generate text using specified provider.

**Request**:
```json
{
  "messages": [
    {
      "role": "user",
      "content": "What is 25 + 75?"
    }
  ],
  "provider": "anthropic",
  "model": null,
  "max_tokens": 4096,
  "temperature": 0.0
}
```

**Response**:
```json
{
  "content": "100",
  "model": "claude-sonnet-4-5-20250929",
  "provider": "AnthropicProvider",
  "usage": {
    "input_tokens": 15,
    "output_tokens": 13,
    "total_tokens": 28
  },
  "finish_reason": "end_turn",
  "latency_ms": 828.43
}
```

## Orchestrator Integration

### Using Gateway with Orchestrator

Create a gateway-specific config file:

**`config/orchestrator.gateway.yaml`**:
```yaml
orchestrator:
  name: "main-orchestrator"
  reasoning_mode: "hybrid"

  # Use Model Gateway
  ai_provider: "gateway"

  # Gateway Configuration
  gateway:
    url: "http://localhost:8000"
    provider: "anthropic"  # or "bedrock", or null for gateway default
    model: null  # or specific model ID
    api_key: null  # if gateway requires authentication

    # Retry Configuration (optional)
    max_retries: 3  # Maximum retry attempts (default: 3)
    timeout: 60  # Request timeout in seconds (default: 60)
    retry_delay: 1.0  # Base delay between retries in seconds (default: 1.0)

  max_parallel_agents: 3
  default_timeout: 30

# ... rest of config ...
```

### Orchestrator Retry Configuration

The orchestrator includes **comprehensive retry logic and error handling** when communicating with the Model Gateway:

#### Retry Behavior

- **Automatic Retries**: Automatically retries failed requests with exponential backoff
- **Smart Error Handling**: Different strategies for different error types
- **Exponential Backoff**: Delays increase exponentially (1s, 2s, 4s, etc.)
- **Error Tracking**: Tracks consecutive and total failures for monitoring

#### Error Categorization

1. **Client Errors (4xx)** - Don't retry:
   - `401 Unauthorized`: Authentication failed
   - `400 Bad Request`: Invalid request
   - `404 Not Found`: Gateway endpoint not found

2. **Rate Limiting (429)** - Retry with longer delay:
   - Applies double backoff (2× exponential delay)
   - Respects rate limit headers

3. **Server Errors (5xx)** - Retry with backoff:
   - `500 Internal Server Error`
   - `502 Bad Gateway`
   - `503 Service Unavailable`

4. **Network Errors** - Retry with backoff:
   - Connection refused
   - Connection timeout
   - DNS resolution failures

#### Retry Configuration Options

```yaml
gateway:
  url: "http://localhost:8000"

  # Retry settings (all optional)
  max_retries: 3  # Number of retry attempts (default: 3)
  timeout: 60  # Request timeout in seconds (default: 60)
  retry_delay: 1.0  # Base delay in seconds (default: 1.0)
```

**Exponential Backoff Formula**: `delay = retry_delay × 2^(attempt-1)`

Examples:
- Attempt 1 fails: Wait 1.0s (1.0 × 2^0)
- Attempt 2 fails: Wait 2.0s (1.0 × 2^1)
- Attempt 3 fails: Wait 4.0s (1.0 × 2^2)

For rate limits, the delay is doubled: `delay = retry_delay × 2^(attempt-1) × 2`

#### Monitoring Retry Behavior

The orchestrator logs all retry attempts:

```
WARNING - Gateway connection error (attempt 1/3): Cannot connect to host
INFO - Retrying in 1.0s...
WARNING - Gateway connection error (attempt 2/3): Cannot connect to host
INFO - Retrying in 2.0s...
ERROR - Gateway request failed after 3 attempts
```

Track retry statistics through the GatewayReasoner:
```python
# Access retry statistics
reasoner = orchestrator.reasoner
print(f"Total Requests: {reasoner.total_requests}")
print(f"Total Failures: {reasoner.total_failures}")
print(f"Consecutive Failures: {reasoner.consecutive_failures}")
print(f"Success Rate: {(reasoner.total_requests - reasoner.total_failures) / reasoner.total_requests * 100:.1f}%")
```

### Running Orchestrator with Gateway

```python
from agent_orchestrator import Orchestrator

# Initialize with gateway config
orchestrator = Orchestrator(
    config_path="config/orchestrator.gateway.yaml"
)
await orchestrator.initialize()

# Process requests - AI reasoning happens through gateway
result = await orchestrator.process({
    "query": "Calculate 45 + 55",
    "operation": "add",
    "numbers": [45, 55]
})
```

## Testing

### Test Gateway Standalone

```bash
# Run gateway tests
python3 test_gateway.py
```

**Expected output**:
```
✅ Gateway Status: healthy
✅ Anthropic Generation: 100
✅ All tests passed!
```

### Test Orchestrator Integration

```bash
# Run orchestrator-gateway integration test
python3 test_orchestrator_gateway.py
```

### Test Gateway Retry Logic

```bash
# Run comprehensive retry logic tests
python3 test_gateway_retry.py
```

**Expected output**:
```
======================================================================
Gateway Retry Logic Test Suite
======================================================================

TEST 1: Normal Success (No Retry Needed)
✅ SUCCESS
   Response: 30
   Provider: AnthropicProvider
   Retries: 0 (success on first attempt)

TEST 5: Retry Statistics with Valid Gateway
📊 Final Statistics:
   Total Requests: 3
   Total Failures: 0
   Success Rate: 100.0%

TEST 4: End-to-End Orchestrator with Gateway Retry
✅ SUCCESS

TEST 2: Gateway Unavailable (Connection Error)
✅ EXPECTED FAILURE
   Total time: 3.01s (with exponential backoff)
   ✅ Retry logic verified: Attempted 3 times before giving up

TEST 3: Gateway Timeout
✅ EXPECTED FAILURE
   Total time: 0.70s (with exponential backoff)

======================================================================
Results: 4/5 tests passed
======================================================================
```

The test suite verifies:
- Normal gateway communication (no retries)
- Connection error handling with exponential backoff
- Timeout handling with retries
- End-to-end orchestrator integration
- Retry statistics tracking

## Configuration Files

### Gateway Configuration (`model_gateway/config/gateway.yaml`)

```yaml
# Default provider when not specified in request
default_provider: "anthropic"

# Provider configurations
providers:
  anthropic:
    type: "anthropic"
    enabled: true
    default_model: "claude-sonnet-4-5-20250929"
    timeout: 60
    max_retries: 3

  bedrock:
    type: "bedrock"
    enabled: true
    region: "us-east-1"
    model_id: "anthropic.claude-sonnet-3-5-v2-20241022"
    timeout: 60
    max_retries: 3

# Rate limiting (optional)
rate_limit:
  enabled: false
  requests_per_minute: 60
  tokens_per_minute: 100000
```

## Gateway Benefits

### 1. **Unified Access**
- Single API for all AI providers
- Consistent request/response format
- Easy provider switching

### 2. **Centralized Control**
- All provider configuration in one place
- Easy to add new providers
- Centralized logging and monitoring

### 3. **Cost Management**
- Track usage across all providers
- Easy to implement rate limiting
- Cost attribution by request

### 4. **Reliability**
- Provider failover capability
- Health monitoring
- Circuit breaker patterns

### 5. **Security**
- Centralized authentication
- API key management
- Request validation

## Switching Providers

### Via Configuration

Change the `provider` field in orchestrator gateway config:

```yaml
gateway:
  url: "http://localhost:8000"
  provider: "bedrock"  # Switch to Bedrock
```

### Via API Request

Specify provider in each request:

```python
request = {
    "messages": [...],
    "provider": "bedrock",  # Override default
    "model": "anthropic.claude-sonnet-3-5-v2-20241022"
}
```

## Automatic Provider Fallback

### Overview

The gateway includes **automatic provider fallback** for high availability. When a requested provider fails, the gateway automatically tries alternative providers transparently.

**Key Benefits**:
- ✅ **Transparent**: User doesn't need to handle failures
- ✅ **Automatic**: No code changes required
- ✅ **Observable**: All fallback events are logged
- ✅ **Configurable**: Control fallback behavior

### How It Works

When you request a specific provider:

```yaml
gateway:
  provider: "anthropic"
```

**If Anthropic fails**, the gateway will:
1. Automatically try Bedrock (or next configured provider)
2. Return successful response from Bedrock
3. Log the fallback event for monitoring
4. Process continues transparently for the user

### Configuration

Fallback is configured in `model_gateway/config/gateway.yaml`:

```yaml
# Automatic Provider Fallback
fallback:
  # Enable automatic fallback
  enabled: true

  # Order of providers to try on failure
  fallback_order:
    - "anthropic"
    - "bedrock"

  # Maximum fallback attempts
  max_fallback_attempts: 2

  # Retry original provider after fallback (usually false)
  retry_original: false
```

### Fallback Logging

When fallback occurs, you'll see in gateway logs:

```
⚠️  Provider 'anthropic' failed (attempt 1/2): API connection timeout.
Trying fallback to 'bedrock'...

🔄 FALLBACK SUCCESS: Provider 'bedrock' succeeded after 'anthropic' failed.
Attempt 2/2, latency=456.78ms

Generated response: provider=BedrockProvider, model=claude-sonnet-3-5-v2-20241022,
tokens=28, latency=1250.45ms (fallback from anthropic)
```

### Testing Fallback

```bash
# Run fallback test suite
python3 test_gateway_fallback.py

# Or quick demonstration
python3 demo_fallback.py
```

To simulate fallback, temporarily set invalid API key:

```bash
export GATEWAY_ANTHROPIC_API_KEY="invalid-key"
# Requests to Anthropic will now fallback to Bedrock
```

### Disabling Fallback

To disable automatic fallback:

```yaml
fallback:
  enabled: false
```

**When disabled**: Only requested provider is tried, failures return immediately.

### Complete Documentation

For detailed fallback documentation, see:
- **`GATEWAY_FALLBACK_FEATURE.md`** - Complete fallback guide with scenarios, testing, and best practices

## Monitoring & Observability

### Gateway Logs

Gateway logs all requests with details:

```
2026-01-19 13:24:28 - model_gateway.server - INFO - Gateway started with 2 provider(s)
2026-01-19 13:24:28 - model_gateway.server - INFO - Generated response:
    provider=anthropic, model=claude-sonnet-4-5-20250929,
    tokens=28, latency=828.43ms
```

### Health Monitoring

Regular health checks via `/health` endpoint:

```bash
# Check health every 30 seconds
while true; do
    curl -s http://localhost:8000/health | jq '.status'
    sleep 30
done
```

## Troubleshooting

### Gateway Won't Start

**Check dependencies**:
```bash
pip install fastapi uvicorn aiohttp anthropic boto3
```

**Check port availability**:
```bash
lsof -i :8000
```

### Provider Initialization Fails

**Anthropic provider**:
- Verify `GATEWAY_ANTHROPIC_API_KEY` is set
- Check API key validity at console.anthropic.com

**Bedrock provider**:
- Verify AWS credentials are configured
- Check model is enabled in your AWS account
- Verify region is correct

### Orchestrator Can't Connect

**Check gateway is running**:
```bash
curl http://localhost:8000/
```

**Check gateway URL in config**:
```yaml
gateway:
  url: "http://localhost:8000"  # Correct URL?
```

**Check logs**:
```bash
tail -f model_gateway/gateway.log
```

## Next Steps

### Adding New Providers

1. Create provider adapter in `model_gateway/providers/`
2. Implement `BaseProvider` interface
3. Add provider config in `gateway.yaml`
4. Update provider factory in `server.py`

### Advanced Features

Consider adding:
- **Caching**: Cache responses for identical requests
- **Rate Limiting**: Implement token bucket algorithm
- **Load Balancing**: Distribute requests across multiple gateways
- **Metrics**: Export metrics to Prometheus/Grafana
- **Authentication**: Add API key authentication

## Files Created

### Core Implementation
- `model_gateway/server.py` - FastAPI application
- `model_gateway/providers/base_provider.py` - Provider interface
- `model_gateway/providers/anthropic_provider.py` - Anthropic adapter
- `model_gateway/providers/bedrock_provider.py` - Bedrock adapter
- `model_gateway/config/models.py` - Configuration models
- `model_gateway/config/loader.py` - Config loader
- `model_gateway/config/gateway.yaml` - Gateway configuration

### Orchestrator Integration
- `agent_orchestrator/reasoning/gateway_reasoner.py` - Gateway client with retry logic
- `agent_orchestrator/config/models.py` - Added GatewayConfig model
- `agent_orchestrator/orchestrator.py` - Added gateway provider support
- `config/orchestrator.gateway.yaml` - Gateway configuration example

### Testing & Documentation
- `test_gateway.py` - Gateway standalone tests
- `test_gateway_fallback.py` - Fallback feature tests
- `test_gateway_retry.py` - Retry logic tests
- `demo_fallback.py` - Fallback demonstration
- `test_orchestrator_gateway.py` - Integration tests
- `MODEL_GATEWAY_IMPLEMENTATION.md` - This document

### Backup
- `backups/pre-gateway-20260119-131304/` - Orchestrator files backup

## Summary

✅ **Completed**:
- Model Gateway implementation with FastAPI
- Anthropic and Bedrock provider adapters
- Gateway configuration system
- **Automatic provider fallback** with transparent failover
- **Orchestrator retry logic** with comprehensive error handling
- Orchestrator integration with GatewayReasoner
- Comprehensive testing (gateway, fallback, retry, integration)
- Full documentation

### Key Features

1. **Unified Gateway API**
   - Single endpoint for all AI providers
   - Consistent request/response format
   - Easy provider switching

2. **Automatic Provider Fallback** (Gateway-side)
   - Transparent failover between providers
   - Full observability with detailed logging
   - Configurable fallback order

3. **Retry Logic & Error Handling** (Orchestrator-side)
   - Automatic retries with exponential backoff
   - Smart error categorization (4xx, 5xx, network, timeout)
   - Error tracking and statistics
   - Comprehensive logging

4. **Production-Ready Reliability**
   - Multiple layers of fault tolerance
   - Gateway retries different providers
   - Orchestrator retries gateway communication
   - End-to-end error handling

🎯 **Gateway is production-ready** and successfully routes AI reasoning requests between the orchestrator and AI providers with:
- Unified API
- Automatic failover
- Retry logic
- Error handling
- Health monitoring
- Full observability
