# Agent Orchestrator API Usage Guide

The Agent Orchestrator now has a **REST API** with **streaming support** for real-time query updates!

## 🚀 Quick Start

### Start the API Server

```bash
# Start with Docker Compose
docker-compose up -d

# Access the API
curl http://localhost:8001/
```

### Send Your First Query

**Streaming (default):**
```bash
curl -N -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "calculate 15 + 27"}'
```

**Non-streaming:**
```bash
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "calculate 15 + 27", "stream": false}'
```

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/query` | POST | Process queries (supports streaming) |
| `/health` | GET | Health check |
| `/stats` | GET | Statistics |
| `/metrics` | GET | Prometheus metrics |
| `/docs` | GET | Interactive API documentation (Swagger UI) |
| `/` | GET | API information |

## 🌊 Streaming with Server-Sent Events (SSE)

The API uses **Server-Sent Events (SSE)** to stream real-time updates as your query progresses.

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

### Example: Streaming with curl

```bash
curl -N -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "calculate 15 + 27",
    "stream": true
  }'
```

**Output:**
```
id: abc123...
event: started
data: {"request_id":"abc123...","session_id":null,"query":"calculate 15 + 27","message":"Query processing started"}

event: security_validation
data: {"message":"Validating input security","enabled":true}

event: reasoning_started
data: {"message":"Determining agent selection","reasoning_mode":"hybrid"}

event: reasoning_complete
data: {"agents_selected":["calculator"],"method":"rule","confidence":1.0,"parallel":false}

event: agents_executing
data: {"agents":["calculator"],"message":"Executing 1 agent(s)"}

event: completed
data: {"success":true,"duration_seconds":0.245,"result":{...}}
```

### Example: Streaming with Python

```python
import requests
import json

def stream_query(query: str):
    response = requests.post(
        "http://localhost:8001/v1/query",
        json={"query": query, "stream": True},
        stream=True,
        headers={"Accept": "text/event-stream"}
    )

    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('event:'):
                event_type = line.split(':', 1)[1].strip()
                print(f"\n[{event_type}]")
            elif line.startswith('data:'):
                data = line.split(':', 1)[1].strip()
                data_json = json.loads(data)
                print(json.dumps(data_json, indent=2))

# Use it
stream_query("calculate 15 + 27")
```

### Example: Streaming with JavaScript (Browser)

```javascript
const eventSource = new EventSource('http://localhost:8001/v1/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query: 'calculate 15 + 27',
    stream: true
  })
});

// Listen to specific events
eventSource.addEventListener('started', (e) => {
  console.log('Started:', JSON.parse(e.data));
});

eventSource.addEventListener('reasoning_complete', (e) => {
  console.log('Reasoning:', JSON.parse(e.data));
});

eventSource.addEventListener('completed', (e) => {
  const result = JSON.parse(e.data);
  console.log('Result:', result.result);
  eventSource.close();
});

eventSource.addEventListener('error', (e) => {
  console.error('Error:', JSON.parse(e.data));
  eventSource.close();
});
```

## 📝 Request Body Schema

### POST /v1/query

**Basic Request:**
```json
{
  "query": "your query here",
  "stream": true,
  "session_id": "optional-session-id"
}
```

**Full Request Schema:**
```json
{
  "query": "query string or natural language request",
  "stream": true,
  "session_id": "optional-session-id",
  "validate_input": true,
  "metadata": {},

  // Optional fields for specific operations
  "operation": "add",
  "operands": [15, 27],
  "data": [...],
  "filters": {},
  "max_results": 5,
  "keywords": ["search", "terms"]
}
```

## 🎯 Usage Examples

### 1. Calculator Operations

**Addition:**
```bash
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "add 15 and 27",
    "operation": "add",
    "operands": [15, 27],
    "stream": false
  }'
```

**Average:**
```bash
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "calculate average",
    "operation": "average",
    "operands": [10, 20, 30, 40, 50],
    "stream": false
  }'
```

### 2. Search Operations

```bash
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "search for Python tutorials",
    "keywords": ["python", "tutorial"],
    "max_results": 5,
    "stream": false
  }'
```

### 3. Data Processing

```bash
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "filter engineering employees",
    "data": [
      {"name": "Alice", "department": "Engineering", "salary": 95000},
      {"name": "Bob", "department": "Sales", "salary": 75000},
      {"name": "Carol", "department": "Engineering", "salary": 105000}
    ],
    "operation": "filter",
    "filters": {
      "conditions": {"department": "Engineering"}
    },
    "stream": false
  }'
```

### 4. Multi-Agent Queries

```bash
curl -N -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "calculate 25 + 75 and search for machine learning",
    "stream": true
  }'
```

## 🔐 Authentication (Optional)

Enable authentication by setting environment variables:

```bash
export ORCHESTRATOR_REQUIRE_AUTH=true
export ORCHESTRATOR_API_KEY="your-secret-key"
```

Then include the API key in requests:

```bash
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-secret-key" \
  -d '{"query": "calculate 15 + 27"}'
```

## 🔍 Health Check

```bash
curl http://localhost:8001/health
```

**Response:**
```json
{
  "status": "healthy",
  "orchestrator": {
    "name": "main-orchestrator",
    "initialized": true,
    "request_count": 42,
    "reasoning_mode": "hybrid"
  },
  "agents": {
    "total": 3,
    "healthy": 3,
    "agents": {
      "calculator": {"healthy": true, "call_count": 15, "success_rate": 1.0},
      "search": {"healthy": true, "call_count": 10, "success_rate": 0.9},
      "data_processor": {"healthy": true, "call_count": 17, "success_rate": 1.0}
    },
    "capabilities": ["calculation", "search", "data-processing"]
  },
  "timestamp": 1705234567.89
}
```

## 📊 Statistics

```bash
curl http://localhost:8001/stats
```

**Response includes:**
- Total requests processed
- Agent statistics (calls, success rates, execution times)
- Reasoning statistics
- Cost tracking (if enabled)
- Circuit breaker status

## 📈 Prometheus Metrics

```bash
# Via API endpoint
curl http://localhost:8001/metrics

# Or dedicated metrics server
curl http://localhost:9090/metrics
```

## 🐍 Python Client Example

```python
import requests
from typing import Optional, Dict, Any

class OrchestratorClient:
    def __init__(self, base_url: str = "http://localhost:8001", api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers["Authorization"] = f"Bearer {api_key}"

    def query(self, query: str, stream: bool = False, **kwargs) -> Dict[str, Any]:
        """Send a query to the orchestrator."""
        payload = {"query": query, "stream": stream, **kwargs}

        if stream:
            return self._stream_query(payload)
        else:
            response = self.session.post(
                f"{self.base_url}/v1/query",
                json=payload
            )
            response.raise_for_status()
            return response.json()

    def _stream_query(self, payload: Dict[str, Any]):
        """Stream query with SSE."""
        response = self.session.post(
            f"{self.base_url}/v1/query",
            json=payload,
            stream=True,
            headers={"Accept": "text/event-stream"}
        )
        response.raise_for_status()

        events = []
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('event:'):
                    event_type = line.split(':', 1)[1].strip()
                    events.append({"type": event_type})
                elif line.startswith('data:'):
                    import json
                    data = line.split(':', 1)[1].strip()
                    if events:
                        events[-1]["data"] = json.loads(data)
                        yield events[-1]

    def health(self) -> Dict[str, Any]:
        """Check health status."""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    def stats(self) -> Dict[str, Any]:
        """Get statistics."""
        response = self.session.get(f"{self.base_url}/stats")
        response.raise_for_status()
        return response.json()

# Usage
client = OrchestratorClient()

# Non-streaming query
result = client.query("calculate 15 + 27", stream=False)
print(result)

# Streaming query
for event in client.query("calculate 15 + 27", stream=True):
    print(f"{event['type']}: {event['data']}")

# Health check
health = client.health()
print(f"Status: {health['status']}")
```

## 🌐 Session Tracking

Track conversations across multiple requests:

```python
import uuid

# Generate a session ID
session_id = str(uuid.uuid4())

# Use the same session_id for related queries
result1 = client.query("calculate 15 + 27", session_id=session_id)
result2 = client.query("now multiply that by 2", session_id=session_id)
```

Session tracking enables:
- Conversation history
- Context preservation
- Session-level metrics
- Debugging multi-request flows

## 🐳 Docker Usage

### Start the API

```bash
# Basic startup
docker-compose up -d

# With monitoring (Jaeger + Prometheus)
docker-compose --profile monitoring up -d
```

### Access Points

| Service | URL | Description |
|---------|-----|-------------|
| Orchestrator API | http://localhost:8001 | Main API endpoint |
| API Docs (Swagger) | http://localhost:8001/docs | Interactive documentation |
| Health Check | http://localhost:8001/health | Health status |
| Metrics | http://localhost:9090/metrics | Prometheus metrics |
| Model Gateway | http://localhost:8585 | AI provider gateway |
| Jaeger UI | http://localhost:16686 | Distributed tracing |
| Prometheus UI | http://localhost:9091 | Metrics visualization |

### Environment Variables

```bash
# API Configuration
ORCHESTRATOR_API_HOST=0.0.0.0
ORCHESTRATOR_API_PORT=8001
ORCHESTRATOR_API_LOG_LEVEL=info

# Authentication (optional)
ORCHESTRATOR_REQUIRE_AUTH=false
ORCHESTRATOR_API_KEY=your-secret-key

# AI Provider Keys
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...

# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
```

## 🔧 Local Development

### Run without Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY="sk-ant-..."
export TAVILY_API_KEY="tvly-..."

# Start the API server
python -m uvicorn agent_orchestrator.api.server:app \
  --host 0.0.0.0 \
  --port 8001 \
  --reload
```

### Access Interactive Docs

Open http://localhost:8001/docs in your browser for:
- Full API documentation
- Try out endpoints interactively
- View request/response schemas
- Test authentication

## 📚 Additional Resources

- [OBSERVABILITY.md](OBSERVABILITY.md) - Metrics, tracing, and logging
- [MONITORING_QUICKSTART.md](MONITORING_QUICKSTART.md) - Quick monitoring setup
- API Docs: http://localhost:8001/docs

## 🎯 Production Considerations

1. **Enable Authentication**: Set `ORCHESTRATOR_REQUIRE_AUTH=true`
2. **Use HTTPS**: Put behind reverse proxy (nginx, Traefik)
3. **Rate Limiting**: Implement at reverse proxy or API gateway level
4. **Monitoring**: Enable full observability stack (Jaeger + Prometheus)
5. **Resource Limits**: Configure Docker resource limits
6. **Logging**: Aggregate logs with ELK Stack or Loki
7. **Scaling**: Run multiple API instances behind load balancer
