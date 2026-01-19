# Running the Orchestrator API Server

This guide shows you how to start and test the Agent Orchestrator API server.

## 🚀 Quick Start

### Option 1: Using Docker Compose (Recommended)

The easiest way to run the API server with all dependencies:

```bash
# Start API + Gateway
docker-compose up -d

# Or with full monitoring (Jaeger + Prometheus)
docker-compose --profile monitoring up -d
```

**Service URLs after startup:**
- **Orchestrator API**: http://localhost:8001
- **Interactive Docs**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health
- **Model Gateway**: http://localhost:8585
- **Jaeger UI** (with monitoring): http://localhost:16686
- **Prometheus** (with monitoring): http://localhost:9091

### Option 2: Using Python Directly

Run the API server locally without Docker:

```bash
# 1. Set environment variables
export ANTHROPIC_API_KEY="sk-ant-..."
export TAVILY_API_KEY="tvly-..."

# 2. Install dependencies (if not already installed)
pip install -r requirements.txt

# 3. Start the API server (same as model_gateway)
python3 -m agent_orchestrator.server
```

**Alternative methods:**

```bash
# Using uvicorn directly
python -m uvicorn agent_orchestrator.api.server:app \
  --host 0.0.0.0 \
  --port 8001 \
  --reload

# Using the API module directly
python -m agent_orchestrator.api.server
```

---

## 🧪 Testing the API

### 1. Check Health Status

```bash
curl http://localhost:8001/health
```

### 2. Send a Test Query (Streaming)

```bash
curl -N -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "calculate 15 + 27"}'
```

### 3. Send a Test Query (Non-Streaming)

```bash
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "calculate 15 + 27", "stream": false}'
```

### 4. Run Automated Tests

```bash
./test_api.sh
```

### 5. Use Interactive Testing Script

The interactive script now uses the API with streaming:

```bash
python test_orchestrator_interactive.py
```

**Features:**
- Real-time streaming responses via Server-Sent Events (SSE)
- Displays reasoning progress, agent selection, and execution
- All commands work through the API
- Health check and stats commands

**Example session:**

```
$ python test_orchestrator_interactive.py

======================================================================
Agent Orchestrator API - Interactive Testing
API Endpoint: http://localhost:8001
======================================================================

Checking API health...
Status: HEALTHY

You > calculate 15 + 27

[Request #1]
Processing: calculate 15 + 27

🌊 Streaming response...

▶ Started: Query processing started
🧠 Reasoning: Determining agent selection (mode: hybrid)
✓ Agents Selected: calculator (confidence: 1.00, sequential)
⚙ Executing: calculator
✅ Completed: 0.245s

✅ SUCCESS

Agents Used: calculator
Execution Time: 0.245s

Result Data:

  calculator:
    Result: 42
    Operation: add
    Expression: 15 + 27
```

---

## 📋 Environment Variables

### Required

```bash
# Anthropic API key (for AI reasoning)
ANTHROPIC_API_KEY=sk-ant-...

# Tavily API key (for search agent)
TAVILY_API_KEY=tvly-...
```

### Optional

```bash
# API Server Configuration
ORCHESTRATOR_API_HOST=0.0.0.0        # Listen address
ORCHESTRATOR_API_PORT=8001            # Port number
ORCHESTRATOR_API_LOG_LEVEL=info       # Log level
ORCHESTRATOR_API_RELOAD=false         # Auto-reload on code changes

# Authentication (optional)
ORCHESTRATOR_REQUIRE_AUTH=false       # Enable API key auth
ORCHESTRATOR_API_KEY=your-secret-key  # API key if auth enabled

# Gateway URL (if running separately)
GATEWAY_URL=http://localhost:8585

# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317  # Jaeger endpoint

# Configuration File
ORCHESTRATOR_CONFIG=/app/config/orchestrator.yaml
```

---

## 🐳 Docker Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Orchestrator API only
docker-compose logs -f orchestrator-api

# Model Gateway only
docker-compose logs -f model-gateway
```

### Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Restart Services

```bash
# Restart orchestrator API
docker-compose restart orchestrator-api

# Restart all services
docker-compose restart
```

### Rebuild After Code Changes

```bash
# Rebuild and restart
docker-compose up -d --build
```

---

## 🔍 Troubleshooting

### API Not Responding

**Check if service is running:**
```bash
docker ps | grep orchestrator-api
```

**Check logs:**
```bash
docker logs orchestrator-api
```

**Check health:**
```bash
curl http://localhost:8001/health
```

### Connection Refused

**Wait for service to start (takes ~30s):**
```bash
sleep 30
curl http://localhost:8001/health
```

### No Agents Registered

**Check orchestrator initialization:**
```bash
docker logs orchestrator-api | grep "agents registered"
```

### Port Already in Use

**If port 8001 is busy, change it:**

In `docker-compose.yml`:
```yaml
ports:
  - "8002:8001"  # Map external 8002 to internal 8001
```

Or set environment variable:
```bash
export ORCHESTRATOR_API_PORT=8002
```

### Interactive Script Can't Connect

**Check API URL:**
```bash
# Set custom API URL
export ORCHESTRATOR_API_URL=http://localhost:8001
python test_orchestrator_interactive.py
```

**Verify API is accessible:**
```bash
curl http://localhost:8001/health
```

---

## 📚 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check with agent status |
| `/stats` | GET | Statistics (requests, agents, costs) |
| `/metrics` | GET | Prometheus metrics |
| `/v1/query` | POST | Process queries (streaming/non-streaming) |
| `/docs` | GET | Interactive Swagger UI documentation |
| `/redoc` | GET | ReDoc API documentation |

---

## 🌊 Streaming API Details

The API uses **Server-Sent Events (SSE)** for real-time streaming.

### Stream Events

| Event | Description | When |
|-------|-------------|------|
| `started` | Query processing started | Immediately |
| `security_validation` | Input validation status | After input received |
| `reasoning_started` | Agent selection in progress | Before reasoning |
| `reasoning_complete` | Agents selected with confidence | After reasoning |
| `agents_executing` | Agents being called | During execution |
| `validation` | Response validation results | After agents complete |
| `completed` | Final result | End of processing |
| `error` | Error occurred | If something fails |

### Example Streaming Flow

```
event: started
data: {"request_id":"abc123...","message":"Query processing started"}

event: reasoning_started
data: {"message":"Determining agent selection","reasoning_mode":"hybrid"}

event: reasoning_complete
data: {"agents_selected":["calculator"],"confidence":1.0}

event: agents_executing
data: {"agents":["calculator"],"message":"Executing 1 agent(s)"}

event: completed
data: {"success":true,"duration_seconds":0.245,"result":{...}}
```

---

## 🔐 Authentication (Optional)

### Enable Authentication

In `.env` or `docker-compose.yml`:
```bash
ORCHESTRATOR_REQUIRE_AUTH=true
ORCHESTRATOR_API_KEY=my-secret-key
```

### Use in Requests

```bash
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer my-secret-key" \
  -d '{"query": "calculate 15 + 27"}'
```

### Interactive Script with Auth

```bash
export ORCHESTRATOR_API_KEY=my-secret-key
python test_orchestrator_interactive.py
```

---

## 📖 Additional Documentation

- **[API_QUICKSTART.md](API_QUICKSTART.md)** - Quick start guide with examples
- **[API_USAGE.md](API_USAGE.md)** - Comprehensive API reference
- **[OBSERVABILITY.md](OBSERVABILITY.md)** - Metrics, tracing, and logging
- **Interactive Docs**: http://localhost:8001/docs

---

## 🎯 Production Deployment

### Recommendations

1. **Enable Authentication**
   ```bash
   ORCHESTRATOR_REQUIRE_AUTH=true
   ORCHESTRATOR_API_KEY=<strong-random-key>
   ```

2. **Use HTTPS**: Deploy behind reverse proxy (nginx, Traefik)

3. **Enable Monitoring**: Use `--profile monitoring` for observability

4. **Set Resource Limits**: Configure Docker resource constraints

5. **Aggregate Logs**: Use ELK Stack or Loki for centralized logging

6. **Scale Horizontally**: Run multiple API instances behind load balancer

### Health Check Configuration

For load balancers and orchestrators:
- **Endpoint**: `GET /health`
- **Expected Status**: 200
- **Expected Response**: `{"status": "healthy"}`
- **Timeout**: 5 seconds
- **Interval**: 30 seconds

---

## ✅ Verification Checklist

After starting the API, verify:

- [ ] API responds at http://localhost:8001
- [ ] Health check returns healthy status
- [ ] Swagger docs accessible at http://localhost:8001/docs
- [ ] Can send streaming queries with curl
- [ ] Can send non-streaming queries with curl
- [ ] Interactive script connects successfully
- [ ] Metrics endpoint returns data
- [ ] Logs show no errors

**Quick verification:**
```bash
# Run all checks
./test_api.sh
```

---

## 🎉 Next Steps

1. **Try Interactive Testing**:
   ```bash
   python test_orchestrator_interactive.py
   ```

2. **Explore Interactive Docs**:
   Open http://localhost:8001/docs in your browser

3. **Enable Monitoring**:
   ```bash
   docker-compose --profile monitoring up -d
   ```

4. **View Distributed Traces**:
   Open http://localhost:16686 (Jaeger UI)

5. **Monitor Metrics**:
   Open http://localhost:9091 (Prometheus UI)

Happy orchestrating! 🎵
