# Observability in Docker

This document explains how to access metrics, traces, and logs when running the Agent Orchestrator and Model Gateway in Docker.

## 📊 Metrics Endpoints

### Model Gateway Metrics
- **URL**: `http://localhost:8585/metrics`
- **Format**: Prometheus exposition format
- **Access**: Available on the same port as the API

**Example:**
```bash
curl http://localhost:8585/metrics
```

**Available Metrics:**
- Request counts and latency (per provider, per model)
- Token usage (input, output, total)
- API costs (per provider, per model)
- Fallback attempts and success rate
- Provider health status
- Active sessions and requests
- Rate limiting metrics

### Orchestrator Metrics
- **URL**: `http://localhost:9090/metrics`
- **Format**: Prometheus exposition format
- **Access**: Dedicated metrics server on port 9090

**Example:**
```bash
curl http://localhost:9090/metrics
```

**Available Metrics:**
- Query metrics (total, success, failed, duration)
- Reasoning metrics (decisions, confidence, duration by mode)
- Agent metrics (calls, duration, retries, fallbacks)
- Validation metrics (checks, confidence, hallucination detection)
- AI reasoner cost and token usage
- Session metrics
- System metrics (active queries, registered agents, circuit breakers)

## 🔍 Distributed Tracing with Jaeger

Jaeger is included in the monitoring profile and automatically configured for both services.

### Quick Start

**Start services with tracing and metrics:**
```bash
docker-compose --profile monitoring up -d
```

**Access Jaeger UI:**
- URL: `http://localhost:16686`
- View distributed traces across Model Gateway → Orchestrator → Agents
- Analyze request flows, latency, and bottlenecks
- Debug errors with full span details

**Jaeger automatically receives traces from:**
- Model Gateway (all API requests, provider calls, fallbacks)
- Orchestrator (queries, reasoning, agent execution, validation)

**Example Trace Flow:**
```
User Request
  → Model Gateway /v1/generate
    → Orchestrator process_query
      → Reasoning (AI/Rule/Hybrid)
      → Agent Execution
        → Agent A call
        → Agent B call (parallel)
      → Response Validation
    ← Results
  ← Response
```

### Configuration

**Already configured in docker-compose.yml:**
```yaml
# Both services automatically send traces to Jaeger
environment:
  - OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
```

**To disable tracing:**
```bash
# Set in docker-compose.yml or .env
OTEL_EXPORTER_OTLP_ENDPOINT=
```

Or update `config/orchestrator.yaml`:
```yaml
observability:
  enable_tracing: false
```

## 🔍 Using Prometheus for Metrics Collection

### Option 1: Manual Prometheus Setup

Create a `prometheus.yml` configuration:

```yaml
scrape_configs:
  - job_name: 'model-gateway'
    static_configs:
      - targets: ['localhost:8585']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'orchestrator'
    static_configs:
      - targets: ['localhost:9090']
    metrics_path: '/metrics'
    scrape_interval: 10s
```

Run Prometheus:
```bash
prometheus --config.file=prometheus.yml
```

### Option 2: Using Docker Compose Profile (Recommended)

We provide pre-configured Prometheus and Jaeger in docker-compose.yml:

**Start with full monitoring stack:**
```bash
docker-compose --profile monitoring up -d
```

This starts:
- Model Gateway (API + metrics)
- Orchestrator (with metrics server)
- Jaeger (distributed tracing)
- Prometheus (metrics collection)

**Access UIs:**
- Jaeger: `http://localhost:16686` - View traces
- Prometheus: `http://localhost:9091` - Query metrics, create graphs, set up alerts

**Example Prometheus Queries:**

Query average orchestrator query duration:
```promql
rate(orchestrator_query_duration_seconds_sum[5m]) / rate(orchestrator_query_duration_seconds_count[5m])
```

Query Model Gateway request rate by provider:
```promql
sum(rate(gateway_requests_total[5m])) by (provider)
```

Query AI reasoner costs over time:
```promql
rate(orchestrator_ai_reasoner_cost_usd[5m])
```

## 📈 Advanced Tracing Features

### Using Custom OTLP Endpoints

By default, traces are sent to Jaeger. You can use other backends:

**Tempo (Grafana):**
```yaml
environment:
  - OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317
```

**Datadog:**
```yaml
environment:
  - OTEL_EXPORTER_OTLP_ENDPOINT=https://trace.agent.datadoghq.com:4317
```

**New Relic:**
```yaml
environment:
  - OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp.nr-data.net:4317
```

### Trace Sampling

To reduce overhead in high-traffic scenarios, configure sampling:

```yaml
environment:
  - OTEL_TRACES_SAMPLER=parentbased_traceidratio
  - OTEL_TRACES_SAMPLER_ARG=0.1  # Sample 10% of traces
```

## 📝 Structured Logs

### Model Gateway Logs
- **Location**: Volume `model-gateway-logs` (mapped to container `/app/model_gateway/logs`)
- **Format**: JSON (machine-parseable)
- **Features**: PII sanitization, correlation IDs, trace IDs
- **Rotation**: Automatic (size-based and time-based)

**View logs:**
```bash
# View live logs
docker logs -f model-gateway

# View log files
docker exec model-gateway ls /app/model_gateway/logs
docker exec model-gateway cat /app/model_gateway/logs/gateway.log
```

### Orchestrator Logs
- **Location**: Configured in `observability.log_file` (default: `logs/orchestrator.log`)
- **Format**: JSON (machine-parseable)
- **Features**: PII sanitization, correlation IDs, trace IDs, session IDs
- **Rotation**: Automatic (10MB default, daily rotation, 30-day retention)

**View logs:**
```bash
# View live logs
docker logs -f orchestrator

# View log files (if volume mounted)
docker exec orchestrator cat /app/logs/orchestrator.log
```

## 🎯 Complete Monitoring Stack

### Start Everything

```bash
# Option 1: Start services only (basic)
docker-compose up -d
# Access: Gateway API (8585), Gateway Metrics (8585/metrics), Orchestrator Metrics (9090/metrics)

# Option 2: Start with full monitoring stack (recommended)
docker-compose --profile monitoring up -d
# Access: All above + Jaeger UI (16686) + Prometheus UI (9091)

# View UIs
open http://localhost:16686  # Jaeger - Distributed Tracing
open http://localhost:9091   # Prometheus - Metrics
```

### Monitoring Endpoints Reference

| Service | Endpoint | Port | Description |
|---------|----------|------|-------------|
| Model Gateway API | `http://localhost:8585` | 8585 | Main API endpoint |
| Model Gateway Metrics | `http://localhost:8585/metrics` | 8585 | Prometheus metrics |
| Orchestrator Metrics | `http://localhost:9090/metrics` | 9090 | Prometheus metrics |
| Jaeger UI | `http://localhost:16686` | 16686 | Distributed tracing UI |
| Prometheus UI | `http://localhost:9091` | 9091 | Metrics visualization |

### Health Checks

**Model Gateway:**
```bash
curl http://localhost:8585/health
```

**Orchestrator:**
Check container health status:
```bash
docker ps | grep orchestrator
```

## 📊 Grafana Dashboards (Optional)

For advanced visualization, add Grafana to docker-compose.yml:

```yaml
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    networks:
      - agent-network
    depends_on:
      - prometheus
```

Then configure Prometheus as a data source and import community dashboards.

## 🔧 Environment Variables for Observability

### Model Gateway

```bash
# Tracing
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
OTEL_CONSOLE=false

# Rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=100/minute
```

### Orchestrator

All observability settings are configured in `config/orchestrator.yaml` under the `observability` section.

## 📦 Docker Compose Commands

```bash
# Start services
docker-compose up -d

# Start with Prometheus monitoring
docker-compose --profile monitoring up -d

# View logs
docker-compose logs -f model-gateway
docker-compose logs -f orchestrator

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Rebuild and restart
docker-compose up -d --build
```

## 🎯 Production Recommendations

1. **Metrics**: Use Prometheus with persistent storage
2. **Tracing**: Deploy Jaeger or use managed services (Tempo, Datadog, New Relic)
3. **Logging**: Use log aggregation (ELK Stack, Loki, CloudWatch)
4. **Alerting**: Configure Prometheus alerts for SLO violations
5. **Dashboards**: Create Grafana dashboards for key metrics
6. **Retention**: Configure appropriate retention policies for metrics and logs

## ❓ Troubleshooting

### Metrics not showing up

1. Check if metrics server started:
```bash
docker logs orchestrator | grep "metrics server"
```

2. Verify port is exposed:
```bash
docker ps | grep orchestrator
# Should show: 0.0.0.0:9090->9090/tcp
```

3. Test metrics endpoint:
```bash
curl http://localhost:9090/metrics
```

### Traces not appearing in Jaeger

1. Check OTLP endpoint is configured
2. Verify Jaeger is running and accessible
3. Check service logs for tracing errors:
```bash
docker logs orchestrator | grep -i "tracing"
```

### High memory usage

Metrics and traces consume memory. If running on constrained resources:
1. Disable tracing: Set `enable_tracing: false`
2. Increase scrape interval in Prometheus
3. Reduce log retention period

## 📚 Further Reading

- [Prometheus Documentation](https://prometheus.io/docs/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Grafana Dashboards](https://grafana.com/grafana/dashboards/)
