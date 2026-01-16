# Interactive Orchestrator Testing

## Overview

The `test_orchestrator_interactive.py` script provides a real-time, interactive interface for testing the agent orchestrator. It allows you to:

- Send queries directly to the orchestrator
- See results in real-time with color-coded output
- View agent selection, reasoning, and execution metadata
- Track performance and statistics
- Test both natural language and JSON-formatted queries

## Setup

Before running the interactive script, make sure you have the dependencies installed:

```bash
# Install dependencies
pip install -r requirements.txt

# (Optional) Set up environment variables for AI reasoning
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

## Quick Start

```bash
# Run the interactive script
python3 test_orchestrator_interactive.py
```

**Note**: The orchestrator will work without `ANTHROPIC_API_KEY` using rule-based routing. AI reasoning is optional but recommended for complex queries.

## Features

### 1. Natural Language Queries

Simply type your query in plain English:

```
You > calculate 15 + 27
You > search for python tutorials
You > find the average of 10, 20, 30
You > multiply 8 by 9
```

The script will automatically parse your query and extract relevant parameters.

### 2. JSON-Formatted Queries

For precise control, use JSON format:

```json
You > {"query": "calculate", "operation": "add", "operands": [15, 27]}
You > {"query": "search", "keywords": ["AI"], "max_results": 5}
You > {"query": "process data", "data": [{"age": 25}, {"age": 30}], "operation": "aggregate"}
```

### 3. Interactive Commands

| Command | Description |
|---------|-------------|
| `/help` or `/h` | Show available commands and query format |
| `/examples` or `/ex` | Show example queries you can try |
| `/stats` or `/s` | Display orchestrator statistics |
| `/quit` or `/q` | Exit the interactive session |

### 4. Color-Coded Output

The script uses colors to make output easy to read:

- **Blue** - Headers and reasoning information
- **Green** - Success status and result data
- **Cyan** - Metadata (agents used, execution time)
- **Yellow** - Warnings
- **Red** - Errors
- **Bold** - Important information

## Output Format

For each query, the script displays:

1. **Success Status** - ✅ SUCCESS or ❌ FAILED
2. **Agents Used** - Which agents were selected (e.g., `calculator → data_processor`)
3. **Execution Time** - Total time taken in seconds
4. **Reasoning Information**:
   - Method (rule-based, AI, or hybrid)
   - Confidence score
   - Explanation
   - Parallel vs sequential execution
5. **Result Data** - The actual output from each agent
6. **Errors** - Any errors that occurred (if applicable)

## Example Session

```
==================================================
Agent Orchestrator - Interactive Testing
==================================================

Type your query or use commands:
  /help     - Show available commands
  /examples - Show example queries
  /stats    - Show orchestrator statistics
  /quit     - Exit the session

==================================================

✅ Orchestrator initialized successfully!
   Agents: 4
   Capabilities: math, calculation, arithmetic, search, data, admin

You > calculate 15 + 27

[Request #1]
Processing: calculate 15 + 27
Parsed as: {
  "query": "calculate 15 + 27",
  "operands": [15, 27],
  "operation": "add"
}

✅ SUCCESS

Agents Used: calculator
Execution Time: 0.023s

Reasoning:
  Method: rule
  Confidence: 0.9
  Explanation: Matched calculation rule

Result Data:

  calculator:
    Result: 42
    Operation: add
    Expression: 15 + 27

──────────────────────────────────────────────────────────────────

You > search for python tutorials

[Request #2]
Processing: search for python tutorials

✅ SUCCESS

Agents Used: search
Execution Time: 0.315s

Reasoning:
  Method: rule
  Confidence: 0.85
  Explanation: Matched search rule

Result Data:

  search:
    Total Results: 5
    Top Results:
      1. Python Tutorial - Beginner's Guide (relevance: 0.95)
      2. Advanced Python Programming (relevance: 0.87)
      3. Python for Data Science (relevance: 0.82)

──────────────────────────────────────────────────────────────────

You > /stats

──────────────────────────────────────────────────────────────────
Orchestrator Statistics:
──────────────────────────────────────────────────────────────────

General:
  Orchestrator Name: main-orchestrator
  Total Requests: 2

Agents:
  Total Agents: 4
  Capabilities: math, calculation, arithmetic, search, data, admin

  Individual Agent Stats:

    • calculator
      Capabilities: math, calculation, arithmetic
      Calls: 1
      Success Rate: 100.0%
      Avg Time: 0.023s
      Healthy: ✅

    • search
      Capabilities: search
      Calls: 1
      Success Rate: 100.0%
      Avg Time: 0.315s
      Healthy: ✅

Reasoning:
  Mode: hybrid
  Rule Matches: 2
  AI Calls: 0

──────────────────────────────────────────────────────────────────

You > /quit

Goodbye!

Cleaning up orchestrator...
✅ Cleanup complete.
```

## Smart Query Parsing

The script automatically recognizes patterns and adds appropriate parameters:

### Math Operations

| Input | Detected Operation | Extracted Operands |
|-------|-------------------|-------------------|
| `calculate 15 + 27` | add | [15, 27] |
| `multiply 8 by 9` | multiply | [8, 9] |
| `divide 100 by 4` | divide | [100, 4] |
| `average of 10, 20, 30` | average | [10, 20, 30] |

### Search Operations

| Input | Added Parameters |
|-------|-----------------|
| `search for python` | `max_results: 5` |
| `find AI tutorials` | `max_results: 5` |

## Multi-Agent Workflows

The script supports complex queries that require multiple agents:

```
You > search for AI tutorials and calculate their average rating
```

The orchestrator will:
1. Use the **search** agent to find tutorials
2. Use the **data_processor** agent to extract ratings
3. Use the **calculator** agent to compute the average
4. Consolidate all outputs into a single response

## Configuration

### Environment Variables

The script respects the following environment variables:

- `ANTHROPIC_API_KEY` - Required for AI-based reasoning (optional for rule-based)
- `DEBUG` - Set to `true` to show full error tracebacks

### Configuration Files

The script loads configuration from:
- `config/orchestrator.yaml` - Main orchestrator configuration
- `config/agents.yaml` - Agent definitions
- `config/rules.yaml` - Routing rules

## Tips for Testing

1. **Start Simple**: Begin with basic queries to understand the system
   ```
   calculate 2 + 2
   search for AI
   ```

2. **Try Different Formats**: Test both natural language and JSON
   ```
   calculate 15 + 27
   {"query": "calculate", "operation": "add", "operands": [15, 27]}
   ```

3. **Use Commands**: Leverage `/examples` to see what queries work

4. **Check Stats**: Use `/stats` to monitor agent performance

5. **Test Edge Cases**: Try unusual queries to see how the orchestrator handles them

6. **Multi-Agent**: Test queries that require multiple agents working together

## Troubleshooting

### "ANTHROPIC_API_KEY not set" Warning

This is expected if you don't have the API key configured. The orchestrator will use rule-based routing instead of AI reasoning. This is fine for testing most queries.

To enable AI reasoning:
1. Get an API key from https://console.anthropic.com/
2. Add to `.env` file: `ANTHROPIC_API_KEY=your_key_here`
3. Restart the script

### "No agents matched the request"

This means the orchestrator couldn't find a suitable agent for your query. Try:
- Using `/examples` to see supported query types
- Being more specific in your query
- Checking if the required agents are configured in `config/agents.yaml`

### Agent Errors

If an agent fails, the output will show the error. Common causes:
- Invalid parameters (e.g., division by zero)
- Missing required fields
- Agent service unavailable (for MCP agents)

## Advanced Usage

### Custom Agent Parameters

You can pass custom parameters to agents:

```json
{
  "query": "calculate",
  "operation": "add",
  "operands": [15, 27],
  "precision": 2
}
```

### Multi-Step Workflows

Request sequential agent execution:

```json
{
  "query": "search and process",
  "steps": ["search", "data_processor"],
  "search_params": {"keywords": ["AI"]},
  "process_params": {"operation": "aggregate"}
}
```

### Parallel Execution

Request parallel agent execution for independent tasks:

```json
{
  "query": "get weather and calculate",
  "agents": ["weather", "calculator"],
  "parallel": true,
  "weather_params": {"city": "Tokyo"},
  "calculator_params": {"operation": "add", "operands": [10, 20]}
}
```

## Integration with Development

This script is perfect for:
- **Development**: Test changes to agents or orchestrator logic
- **Debugging**: See exactly what's happening at each step
- **Demos**: Show the system's capabilities interactively
- **Learning**: Understand how the orchestrator routes requests
- **Performance Testing**: Monitor execution times and agent health

## Next Steps

After getting familiar with the interactive script, you can:

1. **Run the full examples**: `python3 example_usage.py`
2. **Check the test suite**: `pytest tests/`
3. **Read the documentation**: See `README.md` and `AGENT_SELECTION_EXPLAINED.md`
4. **Add new agents**: Follow `AGENT_SETUP_GUIDE.md`
5. **Explore multi-agent workflows**: Run `python3 demo_multi_agent.py`

## Support

For more information:
- **Main README**: `README.md`
- **Agent Selection**: `AGENT_SELECTION_EXPLAINED.md`
- **Multi-Agent**: `MULTI_AGENT_SUMMARY.md`
- **Test Coverage**: `TEST_COVERAGE_SUMMARY.md`
