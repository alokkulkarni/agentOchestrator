# Model Gateway Observability Guide

## Overview

The Model Gateway now includes comprehensive observability features for production monitoring, debugging, and cost tracking. This guide covers all observability capabilities and how to use them.

## Features Implemented

### ✅ 1. Session Tracking & Correlation IDs

**What**: Unique IDs to track requests across services and correlate logs/traces/metrics.

**How it works**:
- **Correlation ID**: Unique ID per request, automatically generated or provided via `X-Correlation-ID` header
- **Session ID**: Tracks multiple requests from the same client via `X-Session-ID` header
- Both IDs are automatically added to logs, traces, and metrics
- IDs are returned in response headers for client-side tracking

**Usage**:
```bash
# Client provides correlation ID
curl -H "X-Correlation-ID: my-request-123" http://localhost:8585/v1/generate

# Gateway generates one if not provided
curl http://localhost:8585/v1/generate
# Response includes: X-Correlation-ID: a1b2c3d4-...

# Track session across multiple requests
curl -H "X-Session-ID: user-session-456" http://localhost:8585/v1/generate
```

**Benefits**:
- Trace requests across distributed systems
- Correlate logs from different services
- Debug specific user sessions
- Track conversation context

---

### ✅ 2. Metrics Aggregation (Prometheus)

**What**: Production-ready metrics for monitoring, alerting, and capacity planning.

**Metrics Collected**:

#### Request Metrics
- `gateway_requests_total` - Total requests by provider, model, status
- `gateway_requests_success_total` - Successful requests
- `gateway_requests_failed_total` - Failed requests by error type
- `gateway_fallback_triggered_total` - Fallback events
- `gateway_fallback_success_total` - Successful fallbacks

#### Latency Metrics (with percentiles)
- `gateway_request_duration_seconds` - End-to-end latency histogram
- `gateway_provider_duration_seconds` - Provider-specific latency by attempt

Percentiles automatically calculated: p50, p90, p95, p99

#### Token Metrics
- `gateway_tokens_consumed_total` - Total tokens by type (input/output/total)
- `gateway_tokens_per_request` - Token distribution histogram

#### Cost Metrics
- `gateway_cost_total_usd` - Cumulative cost by provider/model
- `gateway_cost_per_request_usd` - Cost distribution histogram

#### System Metrics
- `gateway_active_requests` - Current active requests per provider
- `gateway_provider_health` - Provider health status (1=healthy, 0=unhealthy)
- `gateway_provider_health_latency_seconds` - Health check latency
- `gateway_unique_sessions` - Number of tracked sessions
- `gateway_rate_limit_hits_total` - Rate limit violations

#### Payload Metrics
- `gateway_request_size_bytes` - Request payload size histogram
- `gateway_response_size_bytes` - Response payload size histogram

**Endpoints**:
```bash
# Prometheus metrics (for scraping)
curl http://localhost:8585/metrics

# Human-readable stats
curl http://localhost:8585/metrics/stats
```

**Prometheus Configuration**:
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'model-gateway'
    scrape_interval: 15s
    static_configs:
      - targets: ['model-gateway:8585']
    metrics_path: /metrics
```

**Example Queries**:
```promql
# Request rate
rate(gateway_requests_total[5m])

# Success rate
rate(gateway_requests_success_total[5m]) / rate(gateway_requests_total[5m])

# p95 latency
histogram_quantile(0.95, rate(gateway_request_duration_seconds_bucket[5m]))

# Cost per hour
rate(gateway_cost_total_usd[1h]) * 3600

# Active requests
gateway_active_requests

# Fallback rate
rate(gateway_fallback_triggered_total[5m])
```

---

### ✅ 3. Distributed Tracing (OpenTelemetry)

**What**: End-to-end request tracing across services with detailed timing breakdowns.

**Features**:
- Automatic span creation for all requests
- Provider-specific spans for fallback tracking
- Trace context propagation via W3C headers
- Exception recording in spans
- Custom attributes (provider, model, tokens, cost)

**Configuration**:
```bash
# Enable tracing with OTLP collector
export OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317

# Enable console output for debugging
export OTEL_CONSOLE=true

# Start gateway
python -m model_gateway.server
```

**Trace Structure**:
```
generate_request (root span)
├─ provider_attempt_1 (anthropic)
│  └─ [success or exception]
└─ provider_attempt_2 (bedrock) [if fallback]
   └─ [success or exception]
```

**Span Attributes**:
- `provider` - Provider name
- `model` - Model identifier
- `attempt` - Attempt number (for fallback tracking)
- `correlation_id` - Request correlation ID
- `input_tokens` - Token counts
- `output_tokens`
- `cost_usd` - Request cost
- `error` - Exception details (if failed)

**Integration with Jaeger**:
```yaml
# docker-compose.yml
services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # Jaeger UI
      - "4317:4317"    # OTLP gRPC
    environment:
      - COLLECTOR_OTLP_ENABLED=true

  model-gateway:
    environment:
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
```

Access Jaeger UI: `http://localhost:16686`

---

### ✅ 4. Performance Metrics (Percentile Latencies)

**What**: Detailed latency distribution for SLA monitoring and performance tuning.

**Metrics**:
- **p50 (median)**: Typical request latency
- **p90**: 90th percentile (most requests)
- **p95**: 95th percentile (SLA target)
- **p99**: 99th percentile (tail latency)

**Calculation**:
Prometheus histograms with pre-configured buckets:
```
0.01s, 0.025s, 0.05s, 0.1s, 0.25s, 0.5s, 1s, 2.5s, 5s, 10s, 15s, 20s, 30s
```

**Example Queries**:
```promql
# p50 latency by provider
histogram_quantile(0.50,
  rate(gateway_request_duration_seconds_bucket{provider="anthropic"}[5m]))

# p95 latency across all providers
histogram_quantile(0.95,
  rate(gateway_request_duration_seconds_bucket[5m]))

# p99 for specific model
histogram_quantile(0.99,
  rate(gateway_request_duration_seconds_bucket{model="claude-sonnet-4-5"}[5m]))
```

**Grafana Dashboard**:
```json
{
  "title": "Gateway Latency",
  "targets": [
    {
      "expr": "histogram_quantile(0.50, rate(gateway_request_duration_seconds_bucket[5m]))",
      "legendFormat": "p50"
    },
    {
      "expr": "histogram_quantile(0.95, rate(gateway_request_duration_seconds_bucket[5m]))",
      "legendFormat": "p95"
    },
    {
      "expr": "histogram_quantile(0.99, rate(gateway_request_duration_seconds_bucket[5m]))",
      "legendFormat": "p99"
    }
  ]
}
```

---

### ✅ 5. Cost Tracking

**What**: Automatic per-request cost calculation with provider and model pricing.

**Features**:
- Real-time cost calculation based on token usage
- Cost tracking by provider, model, and request
- Cumulative cost statistics
- Cost histograms for distribution analysis

**Pricing Data** (January 2025):

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| Claude Sonnet 4.5 | $3.00 | $15.00 |
| Claude Opus 4.5 | $15.00 | $75.00 |
| Claude 3.5 Sonnet | $3.00 | $15.00 |
| Claude 3 Haiku | $0.25 | $1.25 |

**API Response** includes cost:
```json
{
  "content": "...",
  "model": "claude-sonnet-4-5-20250929",
  "provider": "anthropic",
  "usage": {
    "input_tokens": 150,
    "output_tokens": 800,
    "total_tokens": 950
  },
  "cost_usd": 0.01245,
  "correlation_id": "..."
}
```

**Cost Statistics Endpoint**:
```bash
curl http://localhost:8585/metrics/stats
```

Response:
```json
{
  "cost_tracking": {
    "total_cost_usd": 12.45,
    "total_input_tokens": 150000,
    "total_output_tokens": 800000,
    "total_tokens": 950000,
    "requests_tracked": 1000,
    "average_cost_per_request": 0.01245,
    "cost_by_model": {
      "claude-sonnet-4-5-20250929": 8.50,
      "claude-3-haiku-20240307": 3.95
    },
    "cost_by_provider": {
      "anthropic": 10.00,
      "bedrock": 2.45
    }
  }
}
```

**Custom Pricing**:
```python
from model_gateway.observability.cost_tracking import cost_tracker

# Add custom model pricing
cost_tracker.add_model_pricing(
    model_id="my-custom-model",
    input_price_per_1m=5.00,
    output_price_per_1m=20.00,
    provider="custom",
    tier=PricingTier.STANDARD
)
```

---

### ✅ 6. Rate Limiting with Tracking

**What**: Request rate limiting with detailed violation tracking.

**Features**:
- Per-endpoint rate limits
- Per-client rate limits (by IP, API key, or client ID)
- Rate limit hit tracking and logging
- Integration with metrics

**Configuration**:
```bash
# Enable/disable rate limiting
export RATE_LIMIT_ENABLED=true

# Set default limits (format: "X/minute" or "X/hour")
export RATE_LIMIT_DEFAULT="100/minute"

# Start gateway
python -m model_gateway.server
```

**Custom Limits**:
```python
from model_gateway.observability.rate_limiting import get_rate_limiter

rate_limiter = get_rate_limiter()

# Custom limit for specific endpoint
@app.get("/expensive-operation")
@rate_limiter.create_custom_limit("10/minute")
async def expensive_operation():
    ...
```

**Client Identification**:
Priority order:
1. `X-Client-ID` header
2. Bearer token (hashed)
3. IP address

**Rate Limit Response**:
```json
HTTP/1.1 429 Too Many Requests
Retry-After: 60

{
  "detail": "Rate limit exceeded",
  "correlation_id": "abc123..."
}
```

**Tracking**:
```bash
# Check rate limit stats
curl http://localhost:8585/metrics/stats
```

Metrics:
```promql
# Rate limit hits
gateway_rate_limit_hits_total

# By endpoint
gateway_rate_limit_hits_total{endpoint="/v1/generate"}

# By client
gateway_rate_limit_hits_total{client_id="ip:192.168.1.1"}
```

---

### ✅ 7. PII Sanitization

**What**: Automatic redaction of sensitive data in logs and traces.

**What's Sanitized**:
- Email addresses
- Phone numbers
- API keys (Anthropic, OpenAI, AWS)
- Bearer tokens
- Credit card numbers
- SSN
- IP addresses (optional)
- JWT tokens
- Custom patterns

**Features**:
- Automatic pattern detection
- Partial redaction (show first/last chars)
- Full redaction for sensitive fields
- Custom pattern support

**Examples**:
```python
# Original log
logger.info("User john.doe@example.com requested with key sk-ant-api03-xyz123...")

# Sanitized log
logger.info("User [REDACTED_EMAIL] requested with key sk-an...123...")
```

**Configuration**:
```python
from model_gateway.observability.sanitization import get_sanitizer

sanitizer = get_sanitizer()

# Add custom pattern
sanitizer.add_pattern("custom_id", r"CUST-\d{6}")

# Disable partial redaction
sanitizer.enable_partial_redaction(False)

# Custom redaction text
sanitizer.set_redaction_text("[PRIVATE]")
```

**Sensitive Keys** (always redacted):
- `api_key`, `apikey`
- `secret`, `password`
- `token`, `authorization`
- `credential`, `private_key`
- `access_key`, `secret_key`

---

### ✅ 8. Structured JSON Logging

**What**: Machine-readable logs with automatic field enrichment.

**Features**:
- JSON format for log aggregation systems
- Automatic timestamp (ISO 8601)
- Correlation and trace ID injection
- Log level and logger name
- Contextual fields
- PII sanitization

**Log Format**:
```json
{
  "timestamp": "2026-01-19T14:32:45.123Z",
  "level": "INFO",
  "logger": "model_gateway.server",
  "event": "generation_success",
  "provider": "anthropic",
  "model": "claude-sonnet-4-5-20250929",
  "input_tokens": 150,
  "output_tokens": 800,
  "total_tokens": 950,
  "cost_usd": 0.01245,
  "latency_ms": 456.78,
  "correlation_id": "a1b2c3d4-...",
  "trace_id": "5e6f7g8h9i0j...",
  "span_id": "1k2l3m4n..."
}
```

**Configuration**:
```python
from model_gateway.observability.logging_config import setup_structured_logging

setup_structured_logging(
    log_level="INFO",
    log_file="logs/gateway.log",
    enable_console=True,
    json_format=True,  # JSON format
    enable_rotation=True,
    sanitize_logs=True,
    include_trace_info=True
)
```

**Integration with ELK Stack**:
```yaml
# filebeat.yml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /app/model_gateway/logs/*.log
    json.keys_under_root: true
    json.add_error_key: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "gateway-logs-%{+yyyy.MM.dd}"
```

**Querying in Kibana**:
```
# Find all errors for a correlation ID
correlation_id:"a1b2c3d4-..." AND level:"ERROR"

# Find expensive requests
cost_usd:>1 AND level:"INFO"

# Find slow requests
latency_ms:>5000

# Fallback events
event:"fallback_success" OR event:"provider_failed_fallback"
```

---

### ✅ 9. Log Rotation

**What**: Automatic log file management to prevent disk space issues.

**Features**:
- Size-based rotation (default: 10MB per file)
- Time-based rotation (daily logs)
- Configurable backup retention (default: 5 files)
- Automatic cleanup of old logs

**Configuration**:
```python
setup_structured_logging(
    log_file="logs/gateway.log",
    enable_rotation=True,
    max_bytes=10 * 1024 * 1024,  # 10MB
    backup_count=5  # Keep 5 backups
)
```

**File Structure**:
```
logs/
├── gateway.log (current)
├── gateway.log.1 (previous)
├── gateway.log.2
├── gateway.log.3
├── gateway.log.4
├── gateway.log.5 (oldest)
└── gateway.daily.log (time-based)
    ├── gateway.daily.log.2026-01-19
    ├── gateway.daily.log.2026-01-18
    └── ... (30 days retention)
```

**Docker Volume**:
```yaml
# docker-compose.yml
services:
  model-gateway:
    volumes:
      - gateway-logs:/app/model_gateway/logs

volumes:
  gateway-logs:
    name: model-gateway-logs
```

---

## Environment Variables

Configure observability features via environment variables:

```bash
# Tracing
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317  # OTLP collector
OTEL_CONSOLE=false  # Console tracing for debugging

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=100/minute

# Logging
GATEWAY_LOG_LEVEL=INFO
GATEWAY_LOG_REQUESTS=true
```

---

## Quick Start

### 1. Basic Setup
```bash
# Start gateway with observability
cd model_gateway
python -m model_gateway.server
```

### 2. View Metrics
```bash
# Prometheus format
curl http://localhost:8585/metrics

# Human-readable
curl http://localhost:8585/metrics/stats
```

### 3. Test Request with Tracking
```bash
curl -X POST http://localhost:8585/v1/generate \
  -H "Content-Type: application/json" \
  -H "X-Correlation-ID: test-123" \
  -d '{
    "messages": [{"role": "user", "content": "Hello"}],
    "provider": "anthropic",
    "max_tokens": 100
  }'
```

Response includes:
```json
{
  "content": "Hello! How can I help you?",
  "cost_usd": 0.000315,
  "correlation_id": "test-123",
  "latency_ms": 456.78
}
```

### 4. Check Logs
```bash
# View JSON logs
tail -f model_gateway/logs/gateway.log | jq .
```

---

## Production Deployment

### Prometheus + Grafana Stack
```yaml
# docker-compose.yml
services:
  model-gateway:
    ports:
      - "8585:8585"
    environment:
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
      - RATE_LIMIT_ENABLED=true

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # UI
      - "4317:4317"    # OTLP
    environment:
      - COLLECTOR_OTLP_ENABLED=true
```

Access:
- Gateway: `http://localhost:8585`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`
- Jaeger: `http://localhost:16686`

---

## Troubleshooting

### No Metrics Appearing
```bash
# Check metrics endpoint
curl http://localhost:8585/metrics

# Verify Prometheus scraping
curl http://localhost:9090/api/v1/targets
```

### Tracing Not Working
```bash
# Verify OTLP endpoint
curl http://jaeger:4317/v1/traces

# Check gateway logs
docker logs model-gateway | grep "tracing"
```

### High Cost
```bash
# Check cost breakdown
curl http://localhost:8585/metrics/stats | jq '.cost_tracking'

# Query Prometheus
# Cost by model
sum by (model) (gateway_cost_total_usd)

# Expensive requests
gateway_cost_per_request_usd{quantile="0.99"}
```

---

## Best Practices

1. **Always use correlation IDs** for request tracking
2. **Monitor p95/p99 latencies** for SLA compliance
3. **Set up alerts** on cost thresholds
4. **Enable PII sanitization** in production
5. **Rotate logs** to prevent disk issues
6. **Use structured logging** for searchability
7. **Track fallback rate** to optimize provider selection
8. **Monitor token usage** for cost optimization

---

## Summary

The Model Gateway now provides **production-grade observability** with:

✅ **Correlation & Session IDs** - Track requests across services
✅ **Prometheus Metrics** - 20+ metrics with histograms
✅ **OpenTelemetry Tracing** - Distributed request tracing
✅ **Percentile Latencies** - p50, p95, p99 for SLA monitoring
✅ **Cost Tracking** - Per-request and cumulative costs
✅ **Rate Limiting** - With violation tracking
✅ **PII Sanitization** - Automatic sensitive data redaction
✅ **Structured JSON Logs** - Machine-readable with rotation

All features are **enabled by default** and require **no code changes** to use.
