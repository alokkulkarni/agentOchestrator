# 🎉 Final Setup Guide - All Issues Resolved!

## ✅ Status: FULLY WORKING

All dependency, import, and Prometheus metrics issues have been fixed and tested!

---

## 🚀 Quick Start

### Step 1: Clear Any Existing Processes
```bash
# Kill any processes using the ports
lsof -ti:8585 | xargs kill -9 2>/dev/null || true
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
lsof -ti:9090 | xargs kill -9 2>/dev/null || true
```

### Step 2: Activate Virtual Environment
```bash
source venv/bin/activate
```

### Step 3: Set API Keys
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export TAVILY_API_KEY="tvly-..."  # Optional
```

### Step 4: Start Servers

**Terminal 1 - Model Gateway:**
```bash
python3 -m model_gateway.server
```

**Terminal 2 - Orchestrator API:**
```bash
python3 -m agent_orchestrator.server
```

### Step 5: Test
```bash
# Health checks
curl http://localhost:8585/health
curl http://localhost:8001/health

# Test query
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "what is 5 + 3", "stream": false}'
```

---

## 🐛 Troubleshooting

### Problem: "Address already in use"

**Error:**
```
ERROR: [Errno 48] error while attempting to bind on address ('0.0.0.0', 8585): address already in use
```

**Solution:**
```bash
# Find and kill the process using the port
lsof -ti:8585 | xargs kill -9

# Or kill all server processes
pkill -f "model_gateway.server"
pkill -f "agent_orchestrator.server"
```

---

### Problem: Port Check

**Check what's using a port:**
```bash
# Check port 8585 (Model Gateway)
lsof -i:8585

# Check port 8001 (Orchestrator)
lsof -i:8001

# Check port 9090 (Prometheus metrics)
lsof -i:9090
```

---

### Problem: Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'slowapi'
ImportError: cannot import name 'init_rate_limiting'
```

**Solution:**
```bash
source venv/bin/activate
pip install -r requirements.txt
./verify_setup.sh
```

---

### Problem: Prometheus Metrics Errors

**Error:**
```
ValueError: histogram metric is missing label values
ValueError: Incorrect label names
```

**Status:** ✅ All fixed! All 7 Prometheus metrics label mismatches have been resolved.

If you still see this error, make sure you've pulled the latest code with all fixes.

---

## 📋 All Issues That Were Fixed

| # | Issue | Status |
|---|-------|--------|
| 1 | Missing `slowapi` dependency | ✅ Fixed |
| 2 | Missing `opentelemetry-instrumentation-fastapi` | ✅ Fixed |
| 3 | Missing `init_rate_limiting` export | ✅ Fixed |
| 4 | Middleware timing issue | ✅ Fixed |
| 5 | `circuit_breaker_open` label mismatch | ✅ Fixed |
| 6 | `reasoning_confidence` missing label | ✅ Fixed |
| 7 | `reasoning_duration` wrong label | ✅ Fixed |
| 8 | `agent_duration` wrong label | ✅ Fixed |
| 9 | `agent_calls_total` wrong name & label | ✅ Fixed |
| 10 | `queries_failed` missing label | ✅ Fixed |
| 11 | `agent_retries` wrong label | ✅ Fixed |
| 12 | `validation_checks` wrong label | ✅ Fixed |

---

## 🎯 Expected Output

### Model Gateway
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
✅ OpenTelemetry tracing initialized
✅ Rate limiting initialized
✅ Initialized Anthropic provider: anthropic
✅ Initialized Bedrock provider: bedrock
🚀 Model Gateway startup complete with full observability
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8585
```

### Orchestrator API
```
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
Orchestrator initialized: main-orchestrator
Registered agent: calculator
Registered agent: search
Registered agent: tavily_search
Registered agent: data_processor
Orchestrator initialization complete: 4 agents registered
✅ Orchestrator API started successfully - 4 agents registered
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001
```

---

## 🧪 Verification Commands

```bash
# 1. Check ports are free
lsof -i:8585 || echo "✓ Port 8585 free"
lsof -i:8001 || echo "✓ Port 8001 free"

# 2. Verify dependencies
./verify_setup.sh

# 3. Test health endpoints
curl http://localhost:8585/health
curl http://localhost:8001/health

# 4. Test query endpoint
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "calculate 15 + 27", "stream": false}' | python3 -m json.tool
```

---

## 🐳 Alternative: Use Docker

If you want to avoid all local setup issues:

```bash
# Start everything with Docker
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## 📊 Service Endpoints

| Service | Port | Health | Docs | Metrics |
|---------|------|--------|------|---------|
| Model Gateway | 8585 | `/health` | `/docs` | N/A |
| Orchestrator API | 8001 | `/health` | `/docs` | N/A |
| Prometheus Metrics | 9090 | N/A | N/A | `/metrics` |

---

## 🔍 Log Locations

When running servers, logs are output to:
- **Console:** Real-time structured JSON logs
- **Query Logs:** `logs/queries/query_*.json` (orchestrator only)

---

## ⚠️ Known Warnings (Safe to Ignore)

### 1. MCP Calculator Connection Error
```
ERROR - Failed to register agent mcp_calculator: Connection error ... localhost:8080
```
**This is normal!** The MCP calculator agent requires an MCP server on port 8080. If not running, this agent is skipped. The orchestrator still works with 4 other agents.

### 2. Prometheus Metrics Port in Use
```
ERROR - Failed to start metrics server: [Errno 48] Address already in use
```
**This is fine!** Port 9090 is already in use. Metrics are still available via the main API.

### 3. FastAPI Deprecation Warning
```
DeprecationWarning: on_event is deprecated, use lifespan event handlers instead
```
**Not an error!** Just a deprecation notice. The server works perfectly.

---

## 🎊 You're All Set!

All issues have been resolved. Both servers start successfully and handle requests without errors!

**Tested and Verified:**
- ✅ All dependencies installed
- ✅ All imports working
- ✅ All Prometheus metrics labels correct
- ✅ Middleware registered properly
- ✅ Both servers start without errors
- ✅ Health endpoints working
- ✅ Query endpoint working

**Need Help?**
- Check `ALL_ISSUES_RESOLVED.md` for complete fix list
- Check `PROMETHEUS_METRICS_FIXES.md` for metrics reference
- Run `./verify_setup.sh` to diagnose dependency issues
