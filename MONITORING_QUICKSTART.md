# Monitoring Quick Start 🚀

Get full observability with one command!

## TL;DR

```bash
# Start everything with monitoring
docker-compose --profile monitoring up -d

# Access the UIs
open http://localhost:16686  # Jaeger - Distributed Tracing
open http://localhost:9091   # Prometheus - Metrics Dashboard
```

## What You Get

### 1. Distributed Tracing (Jaeger)
- **URL**: http://localhost:16686
- **What**: End-to-end request tracing across all services
- **Use for**:
  - Debug slow requests
  - Visualize request flows
  - Find bottlenecks
  - Trace errors through the stack

### 2. Metrics Collection (Prometheus)
- **URL**: http://localhost:9091
- **What**: Time-series metrics from both services
- **Use for**:
  - Monitor request rates
  - Track API costs
  - Alert on SLO violations
  - Analyze trends

### 3. Raw Metrics Endpoints
- Gateway: http://localhost:8585/metrics
- Orchestrator: http://localhost:9090/metrics

## Architecture

```
┌─────────────────┐
│  User Request   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│                    Docker Network                        │
│                                                          │
│  ┌─────────────┐  http://jaeger:4317  ┌──────────────┐ │
│  │   Jaeger    │◀──────────────────────│Model Gateway │ │
│  │  (Tracing)  │                       │   :8585      │ │
│  └─────────────┘                       └──────────────┘ │
│         ▲                                      │         │
│         │                                      ▼         │
│         │                               ┌──────────────┐ │
│         │                               │ Orchestrator │ │
│         └───────────────────────────────│    :9090     │ │
│                                         └──────────────┘ │
│         ▲                                      │         │
│         │                                      │         │
│  ┌─────────────┐                              │         │
│  │ Prometheus  │◀─────────────────────────────┘         │
│  │  (Metrics)  │  Scrapes every 10s                     │
│  └─────────────┘                                         │
│                                                          │
└─────────────────────────────────────────────────────────┘
         │
         ▼
   http://localhost:16686 (Jaeger UI)
   http://localhost:9091  (Prometheus UI)
```

## Usage Examples

### View a Trace in Jaeger

1. Open http://localhost:16686
2. Select service: `model-gateway` or `main-orchestrator`
3. Click "Find Traces"
4. Click on any trace to see:
   - Request flow
   - Timing breakdown
   - Span details
   - Errors

### Query Metrics in Prometheus

1. Open http://localhost:9091
2. Go to Graph tab
3. Try these queries:

**Request rate (per second):**
```promql
rate(gateway_requests_total[5m])
```

**Average query duration:**
```promql
rate(orchestrator_query_duration_seconds_sum[5m]) /
rate(orchestrator_query_duration_seconds_count[5m])
```

**Total AI costs (last hour):**
```promql
increase(orchestrator_ai_reasoner_cost_usd[1h])
```

**Error rate:**
```promql
rate(gateway_requests_failed_total[5m])
```

## Start Options

### Basic (no monitoring)
```bash
docker-compose up -d
```
- Services: Gateway + Orchestrator
- Metrics: Available at `/metrics` endpoints
- Tracing: ❌ Not collected

### With Monitoring (recommended)
```bash
docker-compose --profile monitoring up -d
```
- Services: Gateway + Orchestrator + Jaeger + Prometheus
- Metrics: ✅ Collected by Prometheus
- Tracing: ✅ Collected by Jaeger

## Configuration

All pre-configured! But you can customize:

### Change OTLP endpoint
```bash
# In docker-compose.yml or .env
OTEL_EXPORTER_OTLP_ENDPOINT=https://my-collector:4317
```

### Disable tracing
```yaml
# config/orchestrator.yaml
observability:
  enable_tracing: false
```

### Change scrape interval
```yaml
# config/prometheus.yml
scrape_configs:
  - job_name: 'orchestrator'
    scrape_interval: 30s  # Default: 10s
```

## Stop Everything

```bash
# Stop services (keeps data)
docker-compose --profile monitoring down

# Stop and remove volumes (deletes metrics history)
docker-compose --profile monitoring down -v
```

## Troubleshooting

### Jaeger UI shows no traces
- Wait 10-15 seconds after starting
- Make a test request to generate traces
- Check logs: `docker logs model-gateway | grep -i tracing`

### Prometheus shows no data
- Check targets: http://localhost:9091/targets
- Verify endpoints:
  - `curl http://localhost:8585/metrics`
  - `curl http://localhost:9090/metrics`

### Port conflicts
If ports are in use, change them in `docker-compose.yml`:
```yaml
ports:
  - "9092:9090"  # Change 9091 to 9092 for Prometheus
  - "16687:16686"  # Change 16686 to 16687 for Jaeger
```

## Next Steps

1. **Set up alerts**: Configure Prometheus alertmanager
2. **Create dashboards**: Import Grafana + pre-built dashboards
3. **Long-term storage**: Configure Prometheus remote write
4. **Log aggregation**: Add ELK stack or Loki

See [OBSERVABILITY.md](OBSERVABILITY.md) for detailed documentation.
