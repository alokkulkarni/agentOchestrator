# Running Agent Orchestrator & Model Gateway Servers

Quick reference for starting the Agent Orchestrator API and Model Gateway servers.

## 🎯 Consistent Command Pattern

Both services follow the same command pattern for consistency:

| Service | Command |
|---------|---------|
| **Model Gateway** | `python3 -m model_gateway.server` |
| **Orchestrator API** | `python3 -m agent_orchestrator.server` |

---

## 🚀 Quick Start

### Start Both Services with Docker

```bash
# Start both API + Gateway
docker-compose up -d

# With full monitoring (Jaeger + Prometheus)
docker-compose --profile monitoring up -d
```

**Services will be available at:**
- **Orchestrator API**: http://localhost:8001
- **Model Gateway**: http://localhost:8585
- **Jaeger UI**: http://localhost:16686 (with monitoring)
- **Prometheus**: http://localhost:9091 (with monitoring)

---

## 🐍 Running Services Locally (Python)

### 1. Set Environment Variables

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export TAVILY_API_KEY="tvly-..."
```

### 2. Start Model Gateway

```bash
python3 -m model_gateway.server
```

**Output:**
```
Starting Model Gateway server on http://0.0.0.0:8585
```

### 3. Start Orchestrator API (in another terminal)

```bash
python3 -m agent_orchestrator.server
```

**Output:**
```
Starting Agent Orchestrator API Server...
  Host: 0.0.0.0
  Port: 8001

API will be available at: http://localhost:8001
Interactive docs at: http://localhost:8001/docs
```

---

## 🧪 Testing the Services

### Test Model Gateway

```bash
# Health check
curl http://localhost:8585/health

# Send a request
curl -X POST http://localhost:8585/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 100
  }'
```

### Test Orchestrator API

```bash
# Health check
curl http://localhost:8001/health

# Send a query (streaming)
curl -N -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "calculate 15 + 27"}'

# Send a query (non-streaming)
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "calculate 15 + 27", "stream": false}'
```

### Interactive Testing

```bash
# Test orchestrator API (with streaming)
python test_orchestrator_interactive.py
```

---

## 🔧 Configuration

### Model Gateway Environment Variables

```bash
# Server Configuration
GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=8585
GATEWAY_LOG_LEVEL=INFO

# Authentication (optional)
GATEWAY_REQUIRE_AUTH=false
GATEWAY_API_KEY=your-gateway-key

# Provider Keys
GATEWAY_ANTHROPIC_API_KEY=sk-ant-...
```

### Orchestrator API Environment Variables

```bash
# Server Configuration
ORCHESTRATOR_API_HOST=0.0.0.0
ORCHESTRATOR_API_PORT=8001
ORCHESTRATOR_API_LOG_LEVEL=info

# Authentication (optional)
ORCHESTRATOR_REQUIRE_AUTH=false
ORCHESTRATOR_API_KEY=your-orchestrator-key

# AI Provider Keys
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...

# Gateway URL (if using gateway)
GATEWAY_URL=http://localhost:8585
```

---

## 📊 Service Ports Summary

| Service | Port | Metrics Port | Purpose |
|---------|------|--------------|---------|
| Model Gateway | 8585 | 8585 | AI provider gateway |
| Orchestrator API | 8001 | 9090 | Agent orchestration API |
| Jaeger UI | 16686 | - | Distributed tracing |
| Prometheus | 9091 | - | Metrics visualization |

---

## 🐳 Docker Commands

### View Logs

```bash
# Model Gateway logs
docker-compose logs -f model-gateway

# Orchestrator API logs
docker-compose logs -f orchestrator-api

# All logs
docker-compose logs -f
```

### Stop Services

```bash
docker-compose down
```

### Restart Services

```bash
# Restart specific service
docker-compose restart model-gateway
docker-compose restart orchestrator-api

# Restart all
docker-compose restart
```

### Rebuild After Changes

```bash
docker-compose up -d --build
```

---

## 📚 Additional Documentation

### Model Gateway
- Configuration: `model_gateway/config/`
- Observability: Gateway has built-in metrics, tracing, and logging
- Docs: Check `model_gateway/README.md`

### Orchestrator API
- **[API_QUICKSTART.md](API_QUICKSTART.md)** - Quick start guide
- **[API_USAGE.md](API_USAGE.md)** - Full API reference
- **[RUNNING_API_SERVER.md](RUNNING_API_SERVER.md)** - Detailed server setup
- **[OBSERVABILITY.md](OBSERVABILITY.md)** - Metrics and tracing

---

## 🔍 Troubleshooting

### Port Already in Use

**Change ports in docker-compose.yml:**
```yaml
model-gateway:
  ports:
    - "8586:8585"  # Map external 8586 to internal 8585

orchestrator-api:
  ports:
    - "8002:8001"  # Map external 8002 to internal 8001
```

### Cannot Connect to Gateway from Orchestrator

**Check gateway URL in orchestrator:**
```bash
# In Docker, use service name
GATEWAY_URL=http://model-gateway:8585

# When running locally, use localhost
GATEWAY_URL=http://localhost:8585
```

### Service Not Starting

**Check logs:**
```bash
docker logs model-gateway
docker logs orchestrator-api
```

**Check if ports are available:**
```bash
lsof -i :8585  # Model Gateway
lsof -i :8001  # Orchestrator API
```

---

## ✅ Quick Verification

```bash
# 1. Start services
docker-compose up -d

# 2. Wait for startup
sleep 30

# 3. Check health
curl http://localhost:8585/health
curl http://localhost:8001/health

# 4. Run tests
./test_api.sh

# 5. Interactive testing
python test_orchestrator_interactive.py
```

All services running? You're ready to go! 🎉
