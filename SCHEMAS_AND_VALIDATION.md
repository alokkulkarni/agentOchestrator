# Validation Schemas and Agent Testing Guide

## Overview

This document describes all validation schemas for agent outputs and provides comprehensive testing examples for each agent in the orchestrator.

---

## Table of Contents

1. [Validation Schemas](#validation-schemas)
2. [Calculator Agent](#calculator-agent)
3. [Search Agent](#search-agent)
4. [Tavily Search Agent](#tavily-search-agent)
5. [Data Processor Agent](#data-processor-agent)
6. [MCP Calculator Server](#mcp-calculator-server)
7. [Weather Agent (MCP)](#weather-agent-mcp)
8. [Testing All Schemas](#testing-all-schemas)

---

## Validation Schemas

All schemas are located in `config/schemas/` and follow JSON Schema Draft-07 specification.

### Available Schemas

| Schema File | Agent | Purpose |
|-------------|-------|---------|
| `calculation_output.json` | calculator | Validates math operation results |
| `search_output.json` | search | Validates local document search results |
| `tavily_search_output.json` | tavily_search | Validates web search results |
| `data_processor_output.json` | data_processor | Validates data transformation results |
| `weather_output.json` | weather (MCP) | Validates weather data from MCP server |

### Schema Validation Configuration

Agents can specify validation requirements in `config/agents.yaml`:

```yaml
constraints:
  require_validation: true  # Enable schema validation
```

When enabled, the orchestrator:
1. Validates agent output against the corresponding schema
2. Logs validation results
3. Retries on validation failures (configurable)
4. Returns validation metadata with responses

---

## Calculator Agent

### Schema: `calculation_output.json`

**Location**: `config/schemas/calculation_output.json`

**Required Fields**:
- `result` (number): Calculated result
- `operation` (string): Operation performed

**Optional Fields**:
- `operands` (array): Input operands
- `expression` (string): Original expression
- `metadata` (object): Additional info

**Example Output**:
```json
{
  "result": 13,
  "operation": "add",
  "operands": [5, 8],
  "expression": "5 + 8",
  "metadata": {
    "precision": 2,
    "timestamp": "2026-01-18T15:30:00Z"
  }
}
```

### Testing

```bash
# Via orchestrator
python3 test_orchestrator_interactive.py

You > calculate 15 + 27
You > multiply 8 by 9
You > find the average of 10, 20, 30
```

**Direct Test**:
```python
from examples.sample_calculator import calculate

result = calculate(operation="add", operands=[15, 27])
print(result)  # {"result": 42, "operation": "add", ...}
```

---

## Search Agent

### Schema: `search_output.json`

**Location**: `config/schemas/search_output.json`

**Required Fields**:
- `query` (string): Original search query
- `results` (array): Search results
- `total_count` (integer): Total results found

**Result Item Fields**:
- `id` (string): Unique identifier
- `title` (string): Result title
- `content` (string): Content snippet
- `relevance` (number 0-1): Relevance score

**Example Output**:
```json
{
  "query": "Python tutorials",
  "results": [
    {
      "id": "doc_001",
      "title": "Python Tutorial for Beginners",
      "content": "Learn Python programming...",
      "relevance": 0.95,
      "metadata": {"source": "docs"}
    }
  ],
  "total_count": 10,
  "page": 1,
  "has_more": true
}
```

### Testing

```bash
python3 test_orchestrator_interactive.py

You > search for Python tutorials
You > find documents about machine learning
```

---

## Tavily Search Agent

### Schema: `tavily_search_output.json`

**Location**: `config/schemas/tavily_search_output.json`

**Required Fields**:
- `success` (boolean): Search success status
- `query` (string): Original query
- `results` (array): Web search results
- `total_results` (integer): Number of results

**Optional Fields**:
- `answer` (string): AI-generated answer summary
- `images` (array): Relevant images
- `search_depth` (string): "basic" or "advanced"
- `error` (string): Error message if failed

**Example Output**:
```json
{
  "success": true,
  "query": "current weather in London",
  "results": [
    {
      "title": "Weather in London, UK",
      "url": "https://weather.com/london",
      "content": "Current weather is...",
      "score": 0.93
    }
  ],
  "answer": "The current weather in London is 8°C with mist...",
  "total_results": 5,
  "search_depth": "basic",
  "timestamp": "2026-01-18T15:30:00Z"
}
```

### Testing

**Requirements**: Set `TAVILY_API_KEY` in `.env` file

```bash
# Get API key from: https://app.tavily.com/

# Add to .env
echo "TAVILY_API_KEY=tvly-your-key-here" >> .env

# Test
python3 test_orchestrator_interactive.py

You > latest AI news
You > current weather in San Francisco online
You > web search for Python 3.12 features
```

**Direct Test**:
```python
from examples.sample_tavily_search import tavily_search

result = await tavily_search("Python programming", max_results=3)
print(result['answer'])
for r in result['results']:
    print(f"{r['title']}: {r['url']}")
```

---

## Data Processor Agent

### Schema: `data_processor_output.json`

**Location**: `config/schemas/data_processor_output.json`

**Required Fields**:
- `operation` (string): Operation performed
- `input_count` (integer): Input record count
- `output_count` (integer): Output record count
- `result` (array|object): Processed data

**Supported Operations**:
1. **transform**: Select or rename fields
2. **filter**: Filter by conditions
3. **aggregate**: Calculate statistics (count, sum, avg, min, max)
4. **sort**: Sort by field

**Example Output**:
```json
{
  "operation": "aggregate",
  "input_count": 8,
  "output_count": 1,
  "result": {
    "count": 8,
    "salary_avg": 79750.00,
    "salary_sum": 638000,
    "salary_min": 55000,
    "salary_max": 110000
  },
  "filters_applied": {
    "aggregations": ["count", "avg", "sum", "min", "max"]
  }
}
```

### Sample Data

**File**: `examples/sample_data.json`

Contains 8 employee records with fields:
- id, name, department, role
- salary, years_of_service, performance_rating

### Testing

**Run Test Script**:
```bash
python3 examples/test_data_processor.py
```

This script demonstrates all 4 operations with comprehensive examples.

**Via Orchestrator**:
```bash
python3 test_orchestrator_interactive.py

# Note: You'll need to reference the data file or provide inline data

You > process employee data and calculate average salary
You > filter employees in Engineering department
You > sort employees by salary descending
You > aggregate employees grouped by department
```

**Direct Test Examples**:

```python
from examples.sample_data_processor import process_data
import json

# Load sample data
with open('examples/sample_data.json') as f:
    data = json.load(f)

# 1. Transform: Select fields
result = process_data(
    data=data,
    operation="transform",
    filters={"select": ["name", "salary"]}
)

# 2. Filter: Engineering dept only
result = process_data(
    data=data,
    operation="filter",
    filters={"conditions": {"department": "Engineering"}}
)

# 3. Aggregate: Calculate statistics
result = process_data(
    data=data,
    operation="aggregate",
    filters={"aggregations": ["count", "avg", "max"]}
)

# 4. Sort: By salary descending
result = process_data(
    data=data,
    operation="sort",
    filters={"sort_by": "salary", "reverse": True}
)
```

---

## MCP Calculator Server

### About MCP (Model Context Protocol)

MCP is a protocol for communication between AI systems and external tools/services. The MCP calculator demonstrates how to:
- Create an MCP server using FastMCP 2.0
- Register tools (add, subtract, multiply, divide, get_weather)
- Connect the orchestrator to MCP servers
- Handle both HTTP and stdio transports

### Schema: `calculation_output.json`

Uses the same schema as the direct calculator agent.

### Setup and Testing

**Step 1: Start MCP Server**

```bash
# Terminal 1: Start HTTP server
python examples/sample_mcp_server.py --http

# Output:
# Starting Calculator MCP Server...
# ✅ Starting HTTP server on http://localhost:8080
```

**Step 2: Configure Connection**

The MCP calculator is **already enabled** in `config/agents.yaml` (line 310).

Connection options:
```yaml
# Option 1: HTTP transport (requires server running)
url: "http://localhost:8080"

# Option 2: Stdio transport (auto-launches as subprocess)
url: "stdio"
```

**Step 3: Test via Orchestrator**

```bash
# Terminal 2: Run orchestrator
python3 test_orchestrator_interactive.py

# The orchestrator will show 5 agents registered including mcp_calculator

You > add 15 and 27
You > multiply 8 by 9
```

**Direct Server Test**:

```bash
# Test server is running
curl http://localhost:8080/health

# Expected output:
# {"status": "healthy", "server": "Calculator Server", ...}
```

### MCP vs Direct Calculator

| Feature | MCP Calculator | Direct Calculator |
|---------|----------------|-------------------|
| **Transport** | HTTP or stdio | Direct Python call |
| **Setup** | Requires server | No setup |
| **Speed** | ~50-100ms | ~1ms |
| **Use Case** | Microservices, external tools | Local operations |
| **Fallback** | Falls back to direct calculator | N/A |

The orchestrator automatically falls back to the direct calculator if MCP server is unavailable.

---

## Weather Agent (MCP)

### Schema: `weather_output.json`

**Location**: `config/schemas/weather_output.json`

**Required Fields**:
- `city` (string): City name
- `temperature` (number): Temperature value
- `condition` (string): Weather condition
- `humidity` (number 0-100): Humidity percentage
- `unit` (string): Temperature unit

**Example Output**:
```json
{
  "city": "London",
  "temperature": 60,
  "condition": "Cloudy",
  "humidity": 75,
  "unit": "fahrenheit",
  "timestamp": "2026-01-18T15:30:00Z"
}
```

### Setup

**Note**: Currently **disabled** by default (line 373 in agents.yaml)

To enable:

```yaml
# In config/agents.yaml, find weather agent and change:
enabled: false  # Change to true
```

The weather data in `sample_mcp_server.py` includes mock data for:
- New York, London, Tokyo, Paris

---

## Testing All Schemas

### Automated Schema Validation Test

Create a test script to validate all schemas:

```bash
# Create test file
cat > test_all_schemas.py << 'EOF'
#!/usr/bin/env python3
"""Test all validation schemas with sample data."""

import json
from pathlib import Path
from jsonschema import validate, ValidationError

# Test data for each schema
TEST_DATA = {
    "calculation_output.json": {
        "result": 42,
        "operation": "add",
        "operands": [15, 27],
        "expression": "15 + 27"
    },
    "search_output.json": {
        "query": "test",
        "results": [{
            "id": "1",
            "title": "Test",
            "content": "Content",
            "relevance": 0.9
        }],
        "total_count": 1
    },
    "tavily_search_output.json": {
        "success": True,
        "query": "test",
        "results": [{
            "title": "Test",
            "url": "https://example.com",
            "content": "Content"
        }],
        "total_results": 1
    },
    "data_processor_output.json": {
        "operation": "transform",
        "input_count": 5,
        "output_count": 5,
        "result": [{"name": "test"}],
        "filters_applied": {}
    },
    "weather_output.json": {
        "city": "London",
        "temperature": 60,
        "condition": "Cloudy",
        "humidity": 75,
        "unit": "fahrenheit"
    }
}

schemas_dir = Path("config/schemas")

for schema_file, test_data in TEST_DATA.items():
    schema_path = schemas_dir / schema_file
    with open(schema_path) as f:
        schema = json.load(f)

    try:
        validate(instance=test_data, schema=schema)
        print(f"✅ {schema_file}: VALID")
    except ValidationError as e:
        print(f"❌ {schema_file}: INVALID")
        print(f"   Error: {e.message}")

print("\n✅ All schemas tested!")
EOF

# Run test
python3 test_all_schemas.py
```

### Integration Test

Test all agents through the orchestrator:

```bash
python3 test_orchestrator_interactive.py

# Calculator
You > calculate 5 + 8

# Search
You > search for Python

# Tavily (requires API key)
You > latest news online

# Data processor (would need data reference)
# Note: Direct testing recommended for data processor

# MCP Calculator (requires server)
You > add 10 and 20
```

---

## Summary

### Schemas Created

✅ 5 validation schemas covering all agent types:
1. `calculation_output.json` - Math operations
2. `search_output.json` - Local search
3. `tavily_search_output.json` - Web search
4. `data_processor_output.json` - Data operations
5. `weather_output.json` - Weather data (MCP)

### Agents Configured

✅ All agents have validation schemas:
- **calculator** (direct) - ✅ Enabled
- **search** (direct) - ✅ Enabled
- **tavily_search** (direct) - ✅ Enabled (requires API key)
- **data_processor** (direct) - ✅ Enabled
- **mcp_calculator** (MCP) - ✅ Enabled (requires server or stdio)
- **weather** (MCP) - ⚠️  Disabled (enable manually)

### Sample Data

✅ Comprehensive samples provided:
- `examples/sample_data.json` - 8 employee records
- `examples/test_data_processor.py` - Full test suite
- All agents have inline examples in their implementation files

### Next Steps

1. **Set API Keys**:
   ```bash
   echo "TAVILY_API_KEY=your_key_here" >> .env
   ```

2. **Test Data Processor**:
   ```bash
   python3 examples/test_data_processor.py
   ```

3. **Start MCP Server** (optional):
   ```bash
   python examples/sample_mcp_server.py --http
   ```

4. **Run Interactive Tests**:
   ```bash
   python3 test_orchestrator_interactive.py
   ```

---

## Troubleshooting

### Schema Validation Errors

Check `logs/queries/query_*.json` for detailed validation errors:
```bash
cat logs/queries/query_*.json | jq '.validation.validation_details'
```

### Agent Not Available

Check agent registration:
```bash
python3 -c "
from agent_orchestrator import Orchestrator
import asyncio

async def check():
    orch = Orchestrator()
    await orch.initialize()
    stats = orch.get_stats()
    print(f'Registered agents: {stats[\"agents\"][\"total_agents\"]}')
    for agent in stats['agents']['agents']:
        print(f'  - {agent[\"name\"]}: {agent.get(\"is_healthy\")}')
    await orch.cleanup()

asyncio.run(check())
"
```

### MCP Server Connection Issues

1. Check server is running: `curl http://localhost:8080/health`
2. Check firewall settings
3. Try stdio transport instead: Set `MCP_CALC_URL=stdio` in `.env`

---

**Created**: January 18, 2026
**Version**: 1.0
**Status**: ✅ Complete
