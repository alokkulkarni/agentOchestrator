# Model Gateway Architecture Guide

## What is a Model Gateway?

A **Model Gateway** is an intermediary service that sits between your application (orchestrator) and AI model providers (Bedrock, Anthropic, OpenAI, etc.). It acts as a unified access point for all AI model interactions.

```
┌─────────────────┐
│  Orchestrator   │
└────────┬────────┘
         │ HTTP/gRPC
         │
         ▼
┌─────────────────┐
│  Model Gateway  │ ← Your new service
│  (API Service)  │
└────────┬────────┘
         │
         ├─────────────┬─────────────┬─────────────┐
         │             │             │             │
         ▼             ▼             ▼             ▼
   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
   │ Bedrock │   │Anthropic│   │ OpenAI  │   │ Azure   │
   │   API   │   │   API   │   │   API   │   │ OpenAI  │
   └─────────┘   └─────────┘   └─────────┘   └─────────┘
```

---

## Why Build a Model Gateway?

### 1. **Centralized Control & Governance**
- Single point for all AI model access
- Enforce organizational policies
- Audit all model usage
- Compliance and regulatory requirements

### 2. **Cost Management**
- Track costs per team/project/user
- Set spending limits and quotas
- Cost allocation and chargeback
- Budget alerts and notifications

### 3. **Rate Limiting & Quotas**
- Prevent API quota exhaustion
- Fair usage across teams
- Throttle expensive requests
- Priority queuing for critical workloads

### 4. **Security & Access Control**
- Centralized authentication
- Fine-grained authorization (RBAC)
- API key management
- Secrets isolation (orchestrator doesn't need provider keys)

### 5. **Observability**
- Request/response logging
- Performance metrics
- Error tracking
- Usage analytics

### 6. **Reliability**
- Automatic failover between providers
- Circuit breaker patterns
- Retry logic with exponential backoff
- Health checks and monitoring

### 7. **Cost Optimization**
- Response caching (semantic or exact)
- Request deduplication
- Model selection optimization
- Batch processing

### 8. **Multi-Provider Support**
- Unified API across providers
- Easy provider switching
- A/B testing different models
- Load balancing across providers

---

## Model Gateway Architecture

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Model Gateway Service                    │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │   API      │  │   Auth     │  │   Rate     │            │
│  │  Gateway   │→ │  Middleware│→ │  Limiter   │            │
│  └────────────┘  └────────────┘  └────────────┘            │
│         │                                                     │
│         ▼                                                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │  Request   │  │   Cache    │  │   Logging  │            │
│  │ Validator  │→ │   Layer    │→ │  & Metrics │            │
│  └────────────┘  └────────────┘  └────────────┘            │
│         │                                                     │
│         ▼                                                     │
│  ┌────────────────────────────────────────────┐             │
│  │         Router & Load Balancer             │             │
│  │  (Selects provider based on rules/config)  │             │
│  └────────────────────────────────────────────┘             │
│         │                                                     │
│         ├──────────────┬──────────────┬──────────────┐       │
│         ▼              ▼              ▼              ▼       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Bedrock  │  │Anthropic │  │  OpenAI  │  │  Azure   │   │
│  │ Adapter  │  │ Adapter  │  │ Adapter  │  │ Adapter  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│         │              │              │              │       │
└─────────┼──────────────┼──────────────┼──────────────┼──────┘
          │              │              │              │
          ▼              ▼              ▼              ▼
    AWS Bedrock    Anthropic API    OpenAI API    Azure OpenAI
```

### Core Components

#### 1. **API Gateway Layer**
- HTTP/REST API or gRPC service
- Request routing
- Protocol handling (HTTP, WebSocket for streaming)
- API versioning

#### 2. **Authentication & Authorization**
- API key validation
- JWT token verification
- Role-Based Access Control (RBAC)
- Team/project isolation

#### 3. **Rate Limiting**
- Per-user/team/project limits
- Token-based rate limiting
- Sliding window algorithms
- Priority queues

#### 4. **Request Validation**
- Schema validation
- Input sanitization
- Security checks (prompt injection detection)
- Content filtering

#### 5. **Cache Layer**
- Semantic cache (similar queries)
- Exact match cache
- TTL management
- Cache invalidation

#### 6. **Router & Load Balancer**
- Provider selection logic
- Model selection
- Load distribution
- Health-based routing

#### 7. **Provider Adapters**
- Bedrock adapter
- Anthropic adapter
- OpenAI adapter
- Azure OpenAI adapter
- Unified response format

#### 8. **Observability**
- Request/response logging
- Metrics (latency, tokens, cost)
- Distributed tracing
- Error tracking

#### 9. **Storage**
- Usage data (for cost tracking)
- Cache storage (Redis)
- Audit logs (database)
- Configuration (database/config files)

---

## Building the Model Gateway

### Option 1: Build from Scratch

**Technology Stack**:
- **Language**: Python (FastAPI), Go (high performance), Node.js
- **API Framework**: FastAPI, Express, Gin, Echo
- **Cache**: Redis, Memcached
- **Database**: PostgreSQL (usage tracking), MongoDB (logs)
- **Message Queue**: RabbitMQ, Kafka (async processing)
- **Monitoring**: Prometheus, Grafana
- **Tracing**: OpenTelemetry, Jaeger

**Architecture Layers**:

```python
# Pseudo-structure (not actual code, just showing architecture)

model_gateway/
├── api/
│   ├── routes.py              # API endpoints
│   ├── schemas.py             # Request/response schemas
│   └── middleware.py          # Auth, rate limiting
├── core/
│   ├── router.py              # Provider selection logic
│   ├── cache.py               # Caching layer
│   ├── rate_limiter.py        # Rate limiting
│   └── metrics.py             # Metrics collection
├── providers/
│   ├── base.py                # Base provider interface
│   ├── bedrock.py             # Bedrock adapter
│   ├── anthropic.py           # Anthropic adapter
│   ├── openai.py              # OpenAI adapter
│   └── azure.py               # Azure OpenAI adapter
├── storage/
│   ├── database.py            # Usage tracking DB
│   ├── cache_store.py         # Redis connection
│   └── audit_log.py           # Audit logging
└── config/
    ├── settings.py            # Configuration
    └── routing_rules.yaml     # Routing logic
```

**Key Implementation Details**:

1. **Unified API Endpoint**:
```
POST /v1/chat/completions
Content-Type: application/json
Authorization: Bearer <api-key>

{
  "model": "claude-sonnet-4-5",
  "messages": [...],
  "max_tokens": 1000,
  "temperature": 0.0,
  "metadata": {
    "project": "orchestrator",
    "team": "ai-team"
  }
}
```

2. **Provider Adapters**:
Each adapter translates the unified request to provider-specific format:
- Bedrock Converse API format
- Anthropic Messages API format
- OpenAI Chat Completions format
- Azure OpenAI format

3. **Routing Logic**:
```yaml
# routing_rules.yaml
routes:
  - name: "primary"
    condition: "always"
    provider: "bedrock"
    model: "anthropic.claude-sonnet-4-5-20250929"
    fallback: "secondary"

  - name: "secondary"
    condition: "on_failure"
    provider: "anthropic"
    model: "claude-sonnet-4-5-20250929"

  - name: "cost_optimization"
    condition: "tokens < 1000"
    provider: "bedrock"
    model: "anthropic.claude-3-haiku-20240307"
```

### Option 2: Use Existing Open-Source Solutions

#### A. **LiteLLM Proxy**

**What**: Open-source proxy for 100+ LLMs with unified API

**Features**:
- ✅ Unified OpenAI-compatible API
- ✅ Load balancing across providers
- ✅ Fallback routing
- ✅ Rate limiting
- ✅ Cost tracking
- ✅ Caching
- ✅ Prometheus metrics

**Architecture**:
```
┌─────────────┐
│ Orchestrator│
└──────┬──────┘
       │ OpenAI API format
       ▼
┌─────────────┐
│  LiteLLM    │
│   Proxy     │
└──────┬──────┘
       │
       ├─── Bedrock
       ├─── Anthropic
       └─── OpenAI
```

**Setup**:
1. Deploy LiteLLM proxy (Docker, K8s)
2. Configure providers in `config.yaml`
3. Point orchestrator to LiteLLM URL
4. Use OpenAI SDK format

**Configuration Example**:
```yaml
model_list:
  - model_name: claude-sonnet
    litellm_params:
      model: bedrock/anthropic.claude-sonnet-4-5-20250929
      aws_region_name: eu-west-2

  - model_name: claude-sonnet-fallback
    litellm_params:
      model: anthropic/claude-sonnet-4-5-20250929
      api_key: os.environ/ANTHROPIC_API_KEY

router_settings:
  routing_strategy: latency-based-routing
  allowed_fails: 3
  retry_after: 60
```

**Pros**:
- ✅ Quick to deploy
- ✅ Active community
- ✅ Regular updates
- ✅ Good documentation

**Cons**:
- ⚠️ Less customization
- ⚠️ OpenAI API format only
- ⚠️ Python-based (performance)

#### B. **Portkey**

**What**: Enterprise AI gateway with governance and observability

**Features**:
- ✅ Multi-provider support
- ✅ Advanced caching
- ✅ Prompt management
- ✅ Cost tracking
- ✅ Security features
- ✅ Dashboard & analytics

**Architecture**:
```
┌─────────────┐
│ Orchestrator│
└──────┬──────┘
       │ Portkey SDK
       ▼
┌─────────────┐      ┌──────────┐
│  Portkey    │─────▶│ Portkey  │
│  Gateway    │      │ Dashboard│
└──────┬──────┘      └──────────┘
       │
       ├─── Bedrock
       ├─── Anthropic
       └─── OpenAI
```

**Deployment Options**:
- Cloud-hosted (SaaS)
- Self-hosted (Docker, K8s)

**Pros**:
- ✅ Enterprise features
- ✅ Great UI/dashboard
- ✅ Advanced routing
- ✅ Compliance features

**Cons**:
- ⚠️ Commercial product
- ⚠️ Vendor lock-in
- ⚠️ Cost considerations

#### C. **Kong API Gateway + Custom Plugins**

**What**: Enterprise API gateway with plugin architecture

**Features**:
- ✅ Mature API gateway
- ✅ Plugin ecosystem
- ✅ Rate limiting
- ✅ Authentication
- ✅ Analytics
- ✅ High performance

**Architecture**:
```
┌─────────────┐
│ Orchestrator│
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────┐      ┌──────────────┐
│    Kong     │─────▶│ Custom Plugin│
│  Gateway    │      │ (LLM Router) │
└──────┬──────┘      └──────────────┘
       │
       ├─── Bedrock
       ├─── Anthropic
       └─── OpenAI
```

**Setup**:
1. Deploy Kong Gateway
2. Write custom plugin for LLM routing
3. Configure routes and providers
4. Enable plugins (auth, rate limit, logging)

**Pros**:
- ✅ Battle-tested
- ✅ High performance
- ✅ Enterprise ready
- ✅ Flexible

**Cons**:
- ⚠️ Requires custom development
- ⚠️ Complex setup
- ⚠️ Learning curve

#### D. **Helicone**

**What**: LLM observability and caching proxy

**Features**:
- ✅ Zero-latency logging
- ✅ Caching
- ✅ Prompt versioning
- ✅ User analytics
- ✅ Cost tracking

**Architecture**:
```
┌─────────────┐
│ Orchestrator│
└──────┬──────┘
       │ Add Helicone headers
       ▼
┌─────────────┐
│  Helicone   │
│   Proxy     │
└──────┬──────┘
       │
       └─── Provider APIs
```

**Integration**:
Just add HTTP headers to requests:
```
Helicone-Auth: Bearer <api-key>
Helicone-Cache-Enabled: true
```

**Pros**:
- ✅ Simple integration
- ✅ Good caching
- ✅ Nice dashboard

**Cons**:
- ⚠️ Primarily observability
- ⚠️ Limited routing
- ⚠️ SaaS only

### Option 3: Cloud Provider Solutions

#### AWS API Gateway + Lambda

**Architecture**:
```
┌─────────────┐
│ Orchestrator│
└──────┬──────┘
       │ HTTPS
       ▼
┌─────────────┐
│   AWS API   │
│   Gateway   │
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌──────────┐
│  Lambda     │─────▶│ DynamoDB │
│  Function   │      │  (logs)  │
│ (Router)    │      └──────────┘
└──────┬──────┘
       │
       ├─── Bedrock
       ├─── Anthropic (via HTTP)
       └─── OpenAI (via HTTP)
```

**Components**:
- API Gateway: REST API, auth, rate limiting
- Lambda: Routing logic, provider adapters
- DynamoDB: Usage tracking, cache
- CloudWatch: Metrics and logs
- S3: Audit logs

**Pros**:
- ✅ Serverless (no infra management)
- ✅ Auto-scaling
- ✅ Pay per use
- ✅ AWS native

**Cons**:
- ⚠️ AWS vendor lock-in
- ⚠️ Cold start latency
- ⚠️ Complex debugging

#### Azure API Management

Similar to AWS but with Azure services:
- Azure API Management
- Azure Functions
- Azure Cosmos DB
- Application Insights

---

## Connecting Orchestrator to Model Gateway

### Current Architecture (Direct Access)

```python
# In orchestrator
from anthropic import AsyncAnthropic

client = AsyncAnthropic(api_key=api_key)
response = await client.messages.create(
    model="claude-sonnet-4-5-20250929",
    messages=[...]
)
```

### New Architecture (Through Gateway)

The orchestrator would connect to the gateway instead:

```python
# In orchestrator
import httpx  # or aiohttp

# Gateway URL
gateway_url = "https://model-gateway.company.com/v1/chat/completions"

# Make request to gateway
async with httpx.AsyncClient() as client:
    response = await client.post(
        gateway_url,
        headers={
            "Authorization": f"Bearer {gateway_api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "claude-sonnet-4-5",
            "messages": [...],
            "max_tokens": 2000,
            "metadata": {
                "project": "orchestrator",
                "component": "ai_reasoner"
            }
        }
    )
```

### Changes Required in Orchestrator

**No Code Changes Needed!** Just configuration:

1. **Create New Provider Type**: "gateway"
   - Similar to "bedrock" and "anthropic"
   - Uses HTTP client instead of SDK

2. **Configuration**:
```yaml
# config/orchestrator.yaml
orchestrator:
  ai_provider: "gateway"

  gateway:
    url: "https://model-gateway.company.com"
    api_key: "${GATEWAY_API_KEY}"
    model: "claude-sonnet-4-5"
    timeout: 60
```

3. **New Reasoner Class**:
```
agent_orchestrator/reasoning/gateway_reasoner.py
```
- Similar to `bedrock_reasoner.py`
- Makes HTTP calls to gateway
- Handles gateway-specific responses

### API Contract (Gateway Interface)

**Request Format**:
```json
POST /v1/chat/completions
Authorization: Bearer <api-key>
Content-Type: application/json

{
  "model": "claude-sonnet-4-5",
  "messages": [
    {
      "role": "user",
      "content": "Analyze this request and suggest agents..."
    }
  ],
  "max_tokens": 2000,
  "temperature": 0.0,
  "metadata": {
    "project": "orchestrator",
    "team": "ai-platform",
    "request_id": "uuid-here"
  }
}
```

**Response Format**:
```json
{
  "id": "req_abc123",
  "model": "claude-sonnet-4-5",
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "JSON response with agent plan"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 80,
    "total_tokens": 230
  },
  "metadata": {
    "provider": "bedrock",
    "region": "eu-west-2",
    "latency_ms": 234,
    "cost_usd": 0.00345
  }
}
```

---

## Gateway Deployment Architecture

### Development Environment

```
┌─────────────┐
│ Orchestrator│ (localhost:8585)
│   (local)   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Gateway   │ (localhost:8080)
│  (Docker)   │
└──────┬──────┘
       │
       ├─── Bedrock (via AWS credentials)
       └─── Anthropic (via API key)
```

**Docker Compose**:
```yaml
version: '3.8'
services:
  gateway:
    image: model-gateway:latest
    ports:
      - "8080:8080"
    environment:
      - AWS_ACCESS_KEY_ID
      - AWS_SECRET_ACCESS_KEY
      - ANTHROPIC_API_KEY
    volumes:
      - ./config:/config

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: gateway
      POSTGRES_USER: gateway
      POSTGRES_PASSWORD: secret
```

### Production Environment

```
                    ┌─────────────┐
                    │ Load        │
                    │ Balancer    │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
         ┌────▼────┐  ┌───▼─────┐  ┌──▼──────┐
         │ Gateway │  │ Gateway │  │ Gateway │
         │ Node 1  │  │ Node 2  │  │ Node 3  │
         └────┬────┘  └───┬─────┘  └──┬──────┘
              │            │            │
              └────────────┼────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
         ┌────▼────┐  ┌───▼─────┐  ┌──▼──────┐
         │  Redis  │  │Postgres │  │  S3     │
         │ Cluster │  │   RDS   │  │ (logs)  │
         └─────────┘  └─────────┘  └─────────┘
```

**Infrastructure**:
- **Kubernetes** or **ECS** for container orchestration
- **Redis Cluster** for caching
- **PostgreSQL RDS** for usage data
- **S3** for audit logs
- **CloudWatch/Datadog** for monitoring
- **ALB/NLB** for load balancing

**High Availability**:
- Multiple availability zones
- Auto-scaling (CPU/memory based)
- Health checks
- Circuit breakers
- Graceful degradation

---

## Security Considerations

### 1. **Authentication**
- API keys for orchestrator
- JWT tokens for user identification
- mTLS for service-to-service

### 2. **Authorization**
- RBAC (Role-Based Access Control)
- Resource-level permissions
- Team/project isolation

### 3. **Secrets Management**
- Provider API keys in vault (AWS Secrets Manager, HashiCorp Vault)
- Key rotation
- Encrypted at rest and in transit

### 4. **Network Security**
- VPC/Private subnets
- Security groups
- WAF (Web Application Firewall)
- DDoS protection

### 5. **Data Privacy**
- PII detection and masking
- Request/response encryption
- Audit logging
- Compliance (GDPR, HIPAA)

---

## Cost Optimization Features

### 1. **Semantic Caching**
```
User: "What is the capital of France?"
→ Cache: 🔴 MISS
→ Call Provider → "Paris"
→ Store in cache

User: "Tell me the capital city of France?"
→ Cache: 🟢 HIT (semantic similarity > 0.95)
→ Return cached response
→ Save $0.003 + 200ms latency
```

### 2. **Request Deduplication**
```
5 simultaneous requests with same input
→ Gateway calls provider once
→ Broadcasts response to all 5 requesters
→ Save 4x API calls
```

### 3. **Model Selection**
```
If tokens < 1000:
  Use Claude Haiku ($0.25/1M tokens)
Else:
  Use Claude Sonnet ($3/1M tokens)

→ Save ~90% on small requests
```

### 4. **Batch Processing**
```
Queue small requests
→ Batch every 100ms or 10 requests
→ Send as single batch to provider
→ Split responses back to requesters
→ Save on API overhead
```

---

## Monitoring & Observability

### Key Metrics

**1. Request Metrics**:
- Requests per second (RPS)
- Request latency (p50, p95, p99)
- Error rate
- Timeout rate

**2. Provider Metrics**:
- Provider-specific latency
- Provider error rates
- Provider quota usage
- Failover events

**3. Cost Metrics**:
- Tokens per request
- Cost per request
- Cost per team/project
- Daily/monthly spend

**4. Cache Metrics**:
- Cache hit rate
- Cache size
- Cost savings from cache

**5. Quality Metrics**:
- Response quality scores
- Token efficiency
- User satisfaction

### Dashboards

```
┌────────────────────────────────────────┐
│      Model Gateway Dashboard           │
├────────────────────────────────────────┤
│                                        │
│  ┌─────────────┐  ┌─────────────┐    │
│  │   12,450    │  │   234 ms    │    │
│  │ Requests/hr │  │  Avg Latency│    │
│  └─────────────┘  └─────────────┘    │
│                                        │
│  ┌─────────────────────────────────┐  │
│  │     Provider Distribution       │  │
│  │  Bedrock:    65% ████████       │  │
│  │  Anthropic:  30% █████          │  │
│  │  OpenAI:      5% █              │  │
│  └─────────────────────────────────┘  │
│                                        │
│  ┌─────────────────────────────────┐  │
│  │     Cost Tracking               │  │
│  │  Today:    $125.50              │  │
│  │  MTD:      $3,456.78            │  │
│  │  Forecast: $10,234 (on track)   │  │
│  └─────────────────────────────────┘  │
│                                        │
│  ┌─────────────────────────────────┐  │
│  │     Cache Performance           │  │
│  │  Hit Rate:  45%                 │  │
│  │  Savings:   $45.30 today        │  │
│  └─────────────────────────────────┘  │
└────────────────────────────────────────┘
```

---

## Implementation Roadmap

### Phase 1: MVP (2-3 weeks)
- [ ] Basic HTTP API service
- [ ] Single provider adapter (Bedrock)
- [ ] API key authentication
- [ ] Basic logging
- [ ] Docker deployment

### Phase 2: Core Features (3-4 weeks)
- [ ] Multiple provider adapters
- [ ] Routing logic
- [ ] Rate limiting
- [ ] Caching (Redis)
- [ ] Usage tracking
- [ ] Basic monitoring

### Phase 3: Production Ready (4-6 weeks)
- [ ] Advanced routing (failover, load balancing)
- [ ] Cost tracking and quotas
- [ ] Audit logging
- [ ] Dashboard
- [ ] Kubernetes deployment
- [ ] High availability

### Phase 4: Advanced Features (Ongoing)
- [ ] Semantic caching
- [ ] Request deduplication
- [ ] Model optimization
- [ ] A/B testing
- [ ] Prompt management
- [ ] Advanced analytics

---

## Recommended Approach

### For Quick Start: **LiteLLM Proxy**
- Deploy in 1 day
- Good enough for most use cases
- Easy to configure
- Active community

### For Enterprise: **Build Custom Gateway**
- Full control
- Custom business logic
- Integration with existing systems
- Security requirements

### For Managed Solution: **Portkey or Helicone**
- Quick to deploy
- Enterprise features
- Less maintenance
- Cost vs. control tradeoff

---

## Conclusion

A Model Gateway provides:
- ✅ Centralized control
- ✅ Cost optimization
- ✅ Security & compliance
- ✅ Observability
- ✅ Reliability
- ✅ Flexibility

Your orchestrator would connect to the gateway's API instead of directly to Bedrock/Anthropic, gaining all these benefits without changing core orchestration logic.

The gateway becomes the single source of truth for all AI model interactions, making it easier to manage, monitor, and optimize your AI infrastructure.
