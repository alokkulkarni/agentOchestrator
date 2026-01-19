# Tavily Search Agent

## Overview

The Tavily Search Agent provides AI-powered web search capabilities using the [Tavily API](https://tavily.com). Tavily is specifically designed for AI agents and LLMs, providing accurate, real-time search results with source citations.

### Key Features

✅ **Real-Time Web Search** - Access current information from the internet
✅ **AI-Powered Ranking** - Results optimized for LLMs and AI agents
✅ **Source Citations** - Every result includes URL and content snippet
✅ **Answer Summaries** - Optional AI-generated answer from search results
✅ **Domain Filtering** - Include or exclude specific domains
✅ **Configurable Depth** - Basic (faster) or Advanced (comprehensive)
✅ **Image Search** - Optional relevant images in results

---

## Setup

### 1. Get Tavily API Key

1. Visit [https://app.tavily.com/](https://app.tavily.com/)
2. Sign up for an account
3. Get your API key from the dashboard
4. Free tier available with generous limits

### 2. Install Dependencies

```bash
# Install Tavily Python SDK
pip install -r requirements.txt
# or
pip install tavily-python
```

### 3. Configure Environment

Add your API key to `.env`:

```bash
# .env
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxx
```

### 4. Verify Registration

The agent is already registered in `config/agents.yaml`:

```yaml
- name: "tavily_search"
  type: "direct"
  capabilities:
    - "web-search"
    - "real-time-search"
    - "ai-search"
    - "internet"
    - "research"
  enabled: true
```

---

## Usage

### Via Orchestrator (Recommended)

The orchestrator automatically routes queries to Tavily based on keywords:

```python
from agent_orchestrator import Orchestrator

orchestrator = Orchestrator()
await orchestrator.initialize()

# These queries automatically use Tavily:
result = await orchestrator.process({
    "query": "latest news about AI"
})

result = await orchestrator.process({
    "query": "current weather in San Francisco online"
})

result = await orchestrator.process({
    "query": "web search for Python 3.12 features"
})

# Access results
if result['success']:
    tavily_data = result['data']['tavily_search']
    print(f"Found {tavily_data['total_results']} results")

    # AI-generated answer
    if 'answer' in tavily_data:
        print(f"Answer: {tavily_data['answer']}")

    # Search results
    for r in tavily_data['results']:
        print(f"- {r['title']}: {r['url']}")
```

### Direct Agent Call

Call Tavily agent directly for more control:

```python
orchestrator = Orchestrator()
await orchestrator.initialize()

tavily_agent = orchestrator.agent_registry.get("tavily_search")

result = await tavily_agent.call({
    "query": "Claude AI by Anthropic",
    "search_depth": "advanced",  # or "basic"
    "max_results": 5,
    "include_answer": True,
    "include_images": False,
    "include_domains": ["anthropic.com"],  # optional
    "exclude_domains": ["wikipedia.org"],  # optional
})

data = result.data
print(data['answer'])  # AI-generated summary
print(data['results'])  # Search results
```

### Direct Function Call

Use the agent function directly:

```python
from examples.sample_tavily_search import tavily_search

result = await tavily_search(
    query="Python async programming tutorial",
    search_depth="advanced",
    max_results=10,
    include_answer=True,
)

print(result['answer'])
for r in result['results']:
    print(f"{r['title']}: {r['url']} (score: {r['score']})")
```

---

## Parameters

### Input Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | **required** | Search query string |
| `search_depth` | string | "basic" | "basic" (faster) or "advanced" (comprehensive) |
| `max_results` | int | 5 | Number of results (1-20) |
| `include_answer` | bool | true | Include AI-generated answer summary |
| `include_raw_content` | bool | false | Include full page content |
| `include_images` | bool | false | Include relevant images |
| `include_domains` | list | null | Only search these domains |
| `exclude_domains` | list | null | Exclude these domains |

### Output Format

```json
{
  "success": true,
  "query": "Claude AI",
  "results": [
    {
      "title": "Claude AI - Anthropic",
      "url": "https://anthropic.com/claude",
      "content": "Claude is a next generation AI assistant...",
      "score": 0.95,
      "raw_content": null
    }
  ],
  "answer": "Claude is an AI assistant created by Anthropic...",
  "images": [],
  "total_results": 5,
  "search_depth": "basic",
  "timestamp": "2026-01-16T12:00:00Z",
  "metadata": {
    "api": "tavily",
    "version": "1.0",
    "depth": "basic"
  }
}
```

---

## Routing Rules

The orchestrator routes queries to Tavily when they contain:

- "web search"
- "internet search"
- "online"
- "latest"
- "current"
- "real-time"
- "news"

**Priority**: 95 (high - takes precedence over local search)

**Confidence**: 0.90

**Fallback**: Falls back to local `search` agent if Tavily fails

Configuration in `config/rules.yaml`:

```yaml
- name: "web_search_queries"
  priority: 95
  conditions:
    - field: "query"
      operator: "contains"
      value: "latest"
      case_sensitive: false
    # ... more conditions
  logic: "or"
  target_agents:
    - "tavily_search"
  confidence: 0.90
  enabled: true
```

---

## Examples

### Example 1: Latest News

```python
result = await orchestrator.process({
    "query": "latest AI breakthroughs in 2026",
    "max_results": 5,
})

# Result includes:
# - AI-generated answer summary
# - 5 most relevant recent articles
# - Source URLs with scores
```

### Example 2: Research with Domain Filter

```python
tavily_agent = orchestrator.agent_registry.get("tavily_search")

result = await tavily_agent.call({
    "query": "Python async best practices",
    "search_depth": "advanced",
    "max_results": 10,
    "include_domains": ["python.org", "realpython.com", "stackoverflow.com"],
    "include_answer": True,
})

# Only searches within specified domains
# Advanced depth = more comprehensive results
```

### Example 3: News with Images

```python
result = await tavily_agent.call({
    "query": "SpaceX latest launch",
    "max_results": 3,
    "include_answer": True,
    "include_images": True,
})

# Result includes:
# - Text results with news articles
# - Relevant images from the web
# - AI summary of the launch
```

### Example 4: Compare with Local Search

```python
# Web search (Tavily) - for current information
web_result = await orchestrator.process({
    "query": "latest Python 3.12 features online"
})

# Local search - for indexed documents
local_result = await orchestrator.process({
    "query": "search our documentation for Python features"
})
```

---

## Configuration

### Agent Configuration

In `config/agents.yaml`:

```yaml
- name: "tavily_search"
  type: "direct"
  direct_tool:
    module: "examples.sample_tavily_search"
    function: "get_tavily_search"
    is_async: false

  capabilities:
    - "web-search"
    - "real-time-search"
    - "ai-search"
    - "internet"
    - "research"

  role:
    name: "web-researcher"
    description: "AI-powered web search using Tavily API"
    max_execution_time: 30
    guardrails:
      max_results: 20
      safe_search: true
      cache_results: true
      cache_ttl: 3600  # 1 hour

  constraints:
    max_retries: 2
    timeout: 30
    rate_limit: 10  # Respect API limits

  fallback: "search"  # Local search fallback
  enabled: true
```

### Environment Variables

Required in `.env`:

```bash
# Tavily API Key (required)
TAVILY_API_KEY=tvly-your-api-key-here

# Optional: Override default timeout
# ORCHESTRATOR_DEFAULT_TIMEOUT=30
```

---

## API Limits

Tavily API limits vary by plan:

| Plan | Searches/Month | Rate Limit | Features |
|------|----------------|------------|----------|
| **Free** | 1,000 | 60/min | All features |
| **Pro** | 10,000 | 120/min | All features + priority |
| **Enterprise** | Custom | Custom | All + SLA |

**Current Configuration**: 10 requests/minute (conservative)

To adjust: Edit `rate_limit` in `config/agents.yaml`

---

## Error Handling

### Missing API Key

```json
{
  "success": false,
  "error": "TAVILY_API_KEY not found in environment variables",
  "hint": "Set TAVILY_API_KEY in your .env file"
}
```

### API Rate Limit

```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "error_type": "RateLimitError"
}
```

### Fallback Behavior

If Tavily fails, orchestrator automatically falls back to local `search` agent:

```python
# Tavily fails → falls back to local search
result = await orchestrator.process({
    "query": "latest AI news"
})

# Check which agent was actually used
agents_used = result['_metadata']['agent_trail']
if 'tavily_search' in agents_used:
    print("Used Tavily")
elif 'search' in agents_used:
    print("Fell back to local search")
```

---

## Testing

### Run Test Suite

```bash
# Test Tavily agent integration
python3 test_tavily_agent.py
```

### Tests Include

1. ✅ Agent registration verification
2. ✅ Direct API call test
3. ✅ Orchestrator routing test
4. ✅ Fallback behavior test

### Manual Testing

```bash
# Test the agent directly
python3 examples/sample_tavily_search.py

# Test via orchestrator
python3 test_orchestrator_interactive.py

# Then try:
You > web search for latest AI news
You > find current Python 3.12 features online
```

---

## Comparison: Tavily vs Local Search

| Feature | Tavily Search | Local Search |
|---------|---------------|--------------|
| **Data Source** | Real-time web | Local documents |
| **Freshness** | Current | Static |
| **Scope** | Entire internet | Indexed docs only |
| **Answer Summary** | Yes (AI-generated) | No |
| **Speed** | ~1-2s (network) | ~100-300ms |
| **API Key** | Required | None |
| **Cost** | API usage | Free |
| **Best For** | Current info, research | Internal docs, fast queries |

### When to Use Tavily

✅ Latest news or current events
✅ Real-time information
✅ Web research
✅ Fact-checking
✅ Competitive intelligence

### When to Use Local Search

✅ Internal documentation
✅ Fast lookups
✅ No internet needed
✅ Private/confidential data
✅ No API costs

---

## Best Practices

### 1. Use Appropriate Search Depth

```python
# Basic: Faster, good for most queries (< 1s)
result = await tavily_search(
    query="Python basics",
    search_depth="basic"
)

# Advanced: More comprehensive (2-3s)
result = await tavily_search(
    query="deep dive into Python metaclasses",
    search_depth="advanced"
)
```

### 2. Leverage Domain Filtering

```python
# Research from trusted sources
result = await tavily_search(
    query="machine learning fundamentals",
    include_domains=[
        "arxiv.org",
        "papers.nips.cc",
        "openai.com",
        "deepmind.google"
    ]
)

# Exclude domains
result = await tavily_search(
    query="Python tutorial",
    exclude_domains=["w3schools.com"]  # Prefer other sources
)
```

### 3. Optimize Result Count

```python
# Quick answer: 3-5 results
result = await tavily_search(query="...", max_results=3)

# Comprehensive: 10-20 results
result = await tavily_search(query="...", max_results=20)
```

### 4. Use Answer Summaries

```python
# Get AI-generated answer for quick insights
result = await tavily_search(
    query="What is quantum computing?",
    include_answer=True,
    max_results=5
)

print(result['answer'])  # Quick summary
# Then drill into results if needed
```

### 5. Handle Errors Gracefully

```python
result = await orchestrator.process({
    "query": "latest tech news"
})

if not result['success']:
    # Check if fallback was used
    agent_trail = result['_metadata']['agent_trail']
    if 'search' in agent_trail:
        print("Using local search (Tavily unavailable)")
```

---

## Troubleshooting

### Issue: No Results Returned

**Causes**:
- Query too specific
- API rate limit exceeded
- Network connectivity issues

**Solution**:
```python
# Broaden the query
# Check API key is set
# Verify network connection
# Check Tavily dashboard for quota
```

### Issue: Wrong Agent Selected

**Causes**:
- Query doesn't match routing rules
- Rules not configured correctly

**Solution**:
```python
# Be explicit in query:
"web search for..."
"latest online..."
"current news about..."

# Or call directly:
tavily_agent = orchestrator.agent_registry.get("tavily_search")
result = await tavily_agent.call({"query": "..."})
```

### Issue: Slow Responses

**Causes**:
- Network latency
- Using "advanced" search depth
- Large max_results

**Solution**:
```python
# Use basic search
search_depth="basic"

# Reduce results
max_results=3

# Set timeout
timeout=15  # in config
```

---

## Advanced Usage

### Custom Routing

Add your own routing rules in `config/rules.yaml`:

```yaml
- name: "research_queries"
  priority: 98
  conditions:
    - field: "query"
      operator: "contains"
      value: "research"
    - field: "require_web_search"
      operator: "equals"
      value: true
  logic: "or"
  target_agents:
    - "tavily_search"
  confidence: 0.95
  enabled: true
```

### Caching Results

Enable caching in agent config:

```yaml
role:
  guardrails:
    cache_results: true
    cache_ttl: 3600  # 1 hour
```

### Rate Limit Adjustment

For Pro/Enterprise plans:

```yaml
constraints:
  rate_limit: 120  # Adjust based on your plan
```

---

## Resources

- **Tavily Website**: https://tavily.com
- **API Documentation**: https://docs.tavily.com
- **Get API Key**: https://app.tavily.com
- **Python SDK**: https://github.com/tavily-ai/tavily-python
- **Pricing**: https://tavily.com/pricing

---

## Summary

The Tavily Search Agent provides:

✅ Real-time web search via AI-optimized API
✅ Automatic routing from orchestrator
✅ Fallback to local search if unavailable
✅ AI-generated answer summaries
✅ Source citations for every result
✅ Domain filtering and safe search
✅ Configurable search depth
✅ Easy integration with zero code changes

**Status**: ✅ Production-Ready
**Created**: January 16, 2026
**Version**: 1.0
