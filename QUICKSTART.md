# Quick Start Guide

Get up and running with Agent Orchestrator in 5 minutes!

## 1. Install Dependencies

```bash
cd agent_orchestrator
pip install -r requirements.txt
```

## 2. Set Up API Key

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API key
# ANTHROPIC_API_KEY=your_key_here
```

## 3. Run Example

```bash
# Run the example usage script
python example_usage.py
```

## 4. Test Your Installation

```bash
# Run tests to verify everything works
pytest tests/

# Or run with coverage
pytest --cov=agent_orchestrator
```

## 5. Try the Sample Agents

### Calculator (Direct Tool)
```python
from examples.sample_calculator import calculate

result = calculate("add", [10, 5])
print(result)
# Output: {'result': 15, 'operation': 'add', ...}
```

### Search (Async Direct Tool)
```python
import asyncio
from examples.sample_search import search_documents

async def test():
    result = await search_documents("python")
    print(f"Found {result['total_count']} results")

asyncio.run(test())
```

### Data Processor (Direct Tool)
```python
from examples.sample_data_processor import process_data

data = [
    {"name": "Alice", "score": 85},
    {"name": "Bob", "score": 92}
]

result = process_data(data, "aggregate", {"aggregations": ["count", "avg"]})
print(result)
```

## 6. Use the Orchestrator

```python
import asyncio
from agent_orchestrator import Orchestrator

async def main():
    # Initialize
    orch = Orchestrator(config_path="config/orchestrator.yaml")
    await orch.initialize()

    # Process request
    result = await orch.process({
        "query": "calculate 100 divided by 5",
        "operation": "divide",
        "operands": [100, 5]
    })

    print(f"Success: {result['success']}")
    print(f"Result: {result['data']}")

    # Cleanup
    await orch.cleanup()

asyncio.run(main())
```

## Next Steps

1. **Customize Configuration**: Edit files in `config/` directory
2. **Add Your Agents**: Create new agents in `agents.yaml`
3. **Define Routing Rules**: Add rules in `rules.yaml`
4. **Create Custom Tools**: Build your own direct tools or MCP servers
5. **Read Full Documentation**: See `README.md` for detailed guide

## Common Commands

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_agents.py

# Run with verbose output
pytest -v

# Check code quality
ruff check agent_orchestrator/

# Format code
black agent_orchestrator/

# Type checking
mypy agent_orchestrator/
```

## Troubleshooting

**Import Error**: Make sure you're in the project root directory
**API Key Error**: Set `ANTHROPIC_API_KEY` in `.env` file
**Module Not Found**: Run `pip install -r requirements.txt`

## Help & Support

- Full documentation: `README.md`
- Report issues: Create an issue in the repository
- Configuration guide: See `config/` directory for examples

Happy orchestrating! 🎭
