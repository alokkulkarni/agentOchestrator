# Agent Orchestrator API - Quick Start 🚀

Send queries to the orchestrator via REST API with real-time streaming!

## TL;DR

```bash
# Start the services
docker-compose up -d

# Send a query (streaming)
curl -N -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "calculate 15 + 27"}'

# Send a query (non-streaming)
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "calculate 15 + 27", "stream": false}'
```

## 🌊 Streaming Response (Server-Sent Events)

When you send a query with streaming enabled (default), you get **real-time updates** as the orchestrator processes your request:

```bash
$ curl -N -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "calculate 15 + 27"}'

event: started
data: {"request_id":"abc123...","message":"Query processing started"}

event: reasoning_started
data: {"message":"Determining agent selection","reasoning_mode":"hybrid"}

event: reasoning_complete
data: {"agents_selected":["calculator"],"confidence":1.0}

event: agents_executing
data: {"agents":["calculator"],"message":"Executing 1 agent(s)"}

event: completed
data: {"success":true,"duration_seconds":0.245,"result":{"data":{"calculator":{"result":42}}}}
```

## 📡 API Endpoints

| Endpoint | Method | What it does |
|----------|--------|--------------|
| `/v1/query` | POST | Send queries (streaming or non-streaming) |
| `/health` | GET | Check if orchestrator is healthy |
| `/stats` | GET | Get statistics (requests, agents, costs) |
| `/metrics` | GET | Prometheus metrics |
| `/docs` | GET | Interactive API docs (Swagger UI) |

## 🎯 Quick Examples

### Calculator
```bash
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "calculate the average of 10, 20, 30",
    "stream": false
  }'
```

### Search
```bash
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "search for Python tutorials",
    "max_results": 5,
    "stream": false
  }'
```

### Data Processing
```bash
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "filter employees",
    "data": [
      {"name": "Alice", "dept": "Engineering", "salary": 95000},
      {"name": "Bob", "dept": "Sales", "salary": 75000}
    ],
    "operation": "filter",
    "filters": {"conditions": {"dept": "Engineering"}},
    "stream": false
  }'
```

## 🐍 Python Client

```python
import requests

def query_orchestrator(query: str, stream: bool = False):
    response = requests.post(
        "http://localhost:8001/v1/query",
        json={"query": query, "stream": stream}
    )

    if stream:
        # Handle streaming
        for line in response.iter_lines():
            if line:
                print(line.decode('utf-8'))
    else:
        # Handle non-streaming
        result = response.json()
        print(result)

# Use it
query_orchestrator("calculate 15 + 27", stream=False)
```

## 🧪 Test Script

We provide a test script to verify everything works:

```bash
# Run tests
./test_api.sh

# Or specify custom URL
API_URL=http://production-url:8001 ./test_api.sh
```

## 🔗 Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| **API** | http://localhost:8001 | Main API endpoint |
| **Swagger UI** | http://localhost:8001/docs | Interactive docs |
| **Health** | http://localhost:8001/health | Health check |
| **Metrics** | http://localhost:9090/metrics | Prometheus metrics |
| Jaeger | http://localhost:16686 | Distributed tracing (with monitoring profile) |
| Prometheus | http://localhost:9091 | Metrics UI (with monitoring profile) |

## 🎛️ Start Options

```bash
# Basic (API + Gateway)
docker-compose up -d

# With full monitoring (+ Jaeger + Prometheus)
docker-compose --profile monitoring up -d

# View logs
docker-compose logs -f orchestrator-api
```

## 🌐 Session Tracking

Track conversations across multiple queries:

```bash
SESSION_ID=$(uuidgen)

# First query
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"calculate 15 + 27\", \"session_id\": \"$SESSION_ID\", \"stream\": false}"

# Related query in same session
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"multiply that by 2\", \"session_id\": \"$SESSION_ID\", \"stream\": false}"
```

## 📚 Full Documentation

- **[API_USAGE.md](API_USAGE.md)** - Complete API reference with examples
- **[OBSERVABILITY.md](OBSERVABILITY.md)** - Metrics, tracing, and logging
- **Interactive Docs**: http://localhost:8001/docs

## ⚙️ Configuration

Environment variables:

```bash
# API Server
ORCHESTRATOR_API_HOST=0.0.0.0
ORCHESTRATOR_API_PORT=8001

# Authentication (optional)
ORCHESTRATOR_REQUIRE_AUTH=false
ORCHESTRATOR_API_KEY=your-secret-key

# AI Provider
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
```

## 🔐 Enable Authentication

```bash
# Set in .env or docker-compose.yml
ORCHESTRATOR_REQUIRE_AUTH=true
ORCHESTRATOR_API_KEY=my-secret-key

# Use in requests
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer my-secret-key" \
  -d '{"query": "calculate 15 + 27"}'
```

## 🚨 Troubleshooting

**API not responding:**
```bash
# Check if service is running
docker ps | grep orchestrator-api

# Check logs
docker logs orchestrator-api

# Check health
curl http://localhost:8001/health
```

**Connection refused:**
```bash
# Wait for service to start (takes ~30s)
sleep 30
curl http://localhost:8001/health
```

**No agents registered:**
```bash
# Check orchestrator initialization
docker logs orchestrator-api | grep "agents registered"
```

## 🎉 Next Steps

1. Try the interactive docs: http://localhost:8001/docs
2. Enable monitoring: `docker-compose --profile monitoring up -d`
3. View traces in Jaeger: http://localhost:16686
4. Create your own agents (see examples/ directory)
5. Integrate with your application

Happy orchestrating! 🎵
