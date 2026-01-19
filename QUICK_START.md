# Quick Start Guide - Validation Schemas & Agents

## 🚀 Get Started in 5 Minutes

This guide shows you how to quickly test all validation schemas and agents.

---

## Step 1: Install Dependencies

```bash
pip3 install --break-system-packages -r requirements.txt
```

---

## Step 2: Set API Keys (Optional)

For Tavily web search:
```bash
echo "TAVILY_API_KEY=your_tavily_api_key" >> .env
```

Get your key from: https://app.tavily.com/

---

## Step 3: Test Schemas

```bash
python3 test_all_schemas.py
```

**Expected Output**:
```
✅ calculation_output.json: VALID
✅ search_output.json: VALID
✅ tavily_search_output.json: VALID
✅ data_processor_output.json: VALID
✅ weather_output.json: VALID

🎉 All schemas validated successfully!
```

---

## Step 4: Test Data Processor

```bash
python3 examples/test_data_processor.py
```

**Expected Output**:
```
✅ EXAMPLE 1: Transform - Select Fields (8 records)
✅ EXAMPLE 2: Transform - Rename Fields (8 records)
✅ EXAMPLE 3: Filter - By Department (4 records)
✅ EXAMPLE 4: Aggregate - Statistics
✅ EXAMPLE 5: Aggregate - Group By Department
✅ EXAMPLE 6: Sort - By Salary
✅ EXAMPLE 7: Sort - By Years of Service

All examples completed successfully!
```

---

## Step 5: Test Orchestrator

```bash
python3 test_orchestrator_interactive.py
```

**Try These Queries**:

### Calculator
```
You > calculate 5 + 8
You > multiply 15 by 3
You > find the average of 10, 20, 30
```

### Search
```
You > search for Python tutorials
```

### Tavily Web Search (requires API key)
```
You > latest AI news online
You > current weather in San Francisco
```

### Multi-Agent (combines multiple agents)
```
You > current weather in London and add 5 and 8
```

---

## Step 6: Start MCP Server (Optional)

### Option A: HTTP Transport

**Terminal 1** - Start Server:
```bash
python examples/sample_mcp_server.py --http
```

**Terminal 2** - Test:
```bash
python3 test_orchestrator_interactive.py

You > add 10 and 20
```

### Option B: Stdio Transport (Easier)

```bash
# Set in .env
echo "MCP_CALC_URL=stdio" >> .env

# Run orchestrator (will auto-launch MCP server)
python3 test_orchestrator_interactive.py

You > add 10 and 20
```

---

## Example Queries by Agent

### 📊 Data Processor

The data processor works with structured JSON data. Here's how to use it:

**Sample Data**: `examples/sample_data.json` (8 employee records)

**Direct Test**:
```python
from examples.sample_data_processor import process_data
import json

# Load data
with open('examples/sample_data.json') as f:
    data = json.load(f)

# Transform: Select fields
result = process_data(
    data=data,
    operation="transform",
    filters={"select": ["name", "salary"]}
)
print(result)

# Filter: Engineering dept
result = process_data(
    data=data,
    operation="filter",
    filters={"conditions": {"department": "Engineering"}}
)
print(f"Found {result['output_count']} engineers")

# Aggregate: Statistics
result = process_data(
    data=data,
    operation="aggregate",
    filters={"aggregations": ["count", "avg", "max"]}
)
print(result['result'])

# Sort: By salary
result = process_data(
    data=data,
    operation="sort",
    filters={"sort_by": "salary", "reverse": True}
)
print(f"Top earner: {result['result'][0]['name']}")
```

---

## Validation Examples

All agent outputs are validated against their schemas when enabled.

### Check Validation Results

View detailed validation logs:
```bash
# List recent queries
ls -t logs/queries/ | head -5

# View validation for latest query
cat logs/queries/$(ls -t logs/queries/ | head -1) | jq '.validation'
```

**Example Validation Output**:
```json
{
  "timestamp": "2026-01-18T15:30:00Z",
  "is_valid": true,
  "confidence_score": 1.0,
  "hallucination_detected": false,
  "validation_details": {
    "basic_validation": {
      "passed": true,
      "issues": []
    },
    "schema_validation": {
      "passed": true,
      "schema": "calculation_output.json",
      "issues": []
    }
  }
}
```

---

## Troubleshooting

### Issue: Agent Not Found

**Check registered agents**:
```python
from agent_orchestrator import Orchestrator
import asyncio

async def check_agents():
    orch = Orchestrator()
    await orch.initialize()
    stats = orch.get_stats()

    print(f"Total Agents: {stats['agents']['total_agents']}")
    print("\nRegistered Agents:")
    for agent in stats['agents']['agents']:
        status = '✅' if agent.get('is_healthy') else '❌'
        print(f"  {status} {agent['name']}")

    await orch.cleanup()

asyncio.run(check_agents())
```

### Issue: Schema Validation Failed

**Check validation details**:
```bash
# View latest validation error
cat logs/queries/query_*.json | jq '.validation.validation_details.basic_validation.issues'
```

**Common fixes**:
1. Ensure agent output matches schema required fields
2. Check data types (number vs string)
3. Verify enum values match schema

### Issue: MCP Server Not Responding

**Check server status**:
```bash
# Test HTTP server
curl http://localhost:8080/health

# Check process
ps aux | grep sample_mcp_server
```

**Fix**:
1. Restart server: `python examples/sample_mcp_server.py --http`
2. Try stdio transport: Set `MCP_CALC_URL=stdio` in `.env`
3. Check firewall/port availability

### Issue: Tavily API Key Error

**Error**: `TAVILY_API_KEY not found in environment variables`

**Fix**:
```bash
# Add to .env
echo "TAVILY_API_KEY=tvly-your-key-here" >> .env

# Verify
python3 -c "from dotenv import load_dotenv; import os; load_dotenv(); print('Key set:', bool(os.getenv('TAVILY_API_KEY')))"
```

---

## Quick Commands Reference

```bash
# Validate all schemas
python3 test_all_schemas.py

# Test data processor with samples
python3 examples/test_data_processor.py

# Run interactive orchestrator
python3 test_orchestrator_interactive.py

# Start MCP server (HTTP)
python examples/sample_mcp_server.py --http

# Start MCP server (stdio)
python examples/sample_mcp_server.py

# Check logs
ls -t logs/queries/ | head -5

# View latest query
cat logs/queries/$(ls -t logs/queries/ | head -1) | jq '.'
```

---

## What's Available

### ✅ Enabled Agents (5)

1. **calculator** (Direct) - Math operations
2. **search** (Direct) - Local document search
3. **tavily_search** (Direct) - Web search (requires API key)
4. **data_processor** (Direct) - Data transformations
5. **mcp_calculator** (MCP) - Calculator via MCP protocol

### ⚠️ Disabled Agents (1)

1. **weather** (MCP) - Weather data (can be enabled)

### 📋 Validation Schemas (5)

1. `calculation_output.json` - Math results
2. `search_output.json` - Search results
3. `tavily_search_output.json` - Web search results
4. `data_processor_output.json` - Data processing results
5. `weather_output.json` - Weather data

### 📊 Sample Data (1)

1. `examples/sample_data.json` - 8 employee records

---

## Next Steps

1. ✅ **Read Full Documentation**: `SCHEMAS_AND_VALIDATION.md`
2. ✅ **View Implementation Summary**: `VALIDATION_SCHEMAS_SUMMARY.md`
3. ✅ **Explore MCP Integration**: `examples/sample_mcp_server.py`
4. ✅ **Customize Schemas**: Add your own in `config/schemas/`
5. ✅ **Create Sample Data**: Add domain-specific datasets

---

## Support

For detailed documentation:
- **Validation Guide**: `SCHEMAS_AND_VALIDATION.md` (890 lines)
- **Summary**: `VALIDATION_SCHEMAS_SUMMARY.md`
- **Multi-Agent Fix**: `MULTI_AGENT_FIX.md`
- **Tavily Agent**: `TAVILY_AGENT.md`

For issues or questions:
- Check `logs/queries/` for detailed execution logs
- Review agent configurations in `config/agents.yaml`
- Validate schemas with `test_all_schemas.py`

---

**Status**: ✅ All systems operational
**Agents**: 5/6 enabled (83%)
**Schemas**: 5/5 validated (100%)
**Sample Data**: Ready to use

🎉 **Ready to start testing!**
