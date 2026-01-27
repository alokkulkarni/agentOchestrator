# Agent Orchestrator

**A production-ready, intelligent agent coordination framework for building multi-agent systems with hybrid AI reasoning**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Test Coverage](https://img.shields.io/badge/coverage-65%25-yellow.svg)](TEST_COVERAGE_SUMMARY.md)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.0-purple.svg)](https://github.com/jlowin/fastmcp)

---

## 🎯 Overview

Agent Orchestrator is a powerful framework for building intelligent multi-agent systems. It provides a central orchestrator (supervisor) that intelligently routes requests to the appropriate agents based on their capabilities, using a hybrid approach combining rule-based and AI-powered reasoning.

**Key Features:**
- 🧠 **Hybrid Reasoning**: Rule-based (fast) + AI-based (intelligent) agent selection
- 🎯 **Multi-Agent Orchestration**: Automatically distribute requests across multiple agents and consolidate outputs
- 📦 **Central Registry**: Stores all agent characteristics with O(1) capability lookup
- 🔌 **Multiple Agent Types**: Direct Python functions and MCP protocol servers
- 🛡️ **Security Built-in**: Input validation, role-based access control, approval workflows
- ⚡ **High Performance**: Async execution, parallel agent calls, circuit breakers
- 📊 **Observable**: Comprehensive metrics, audit logging, health monitoring
- 🎛️ **Configuration-Driven**: YAML-based setup, no hardcoding
- 💬 **Conversational UX**: Human-like responses with natural follow-ups and graceful session closing ✨ *NEW*
- 🔐 **Policy Enforcement**: Configurable evaluators for action validation and constraint checking ✨ *NEW*

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                                │
│                  {"query": "calculate 2 + 2"}                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR                                   │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              Security Validation                             │  │
│  │  • Input sanitization  • Command injection prevention        │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                             │                                       │
│                             ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │           REASONING ENGINE (Hybrid)                          │  │
│  │                                                              │  │
│  │  ┌──────────────┐      ┌──────────────┐                    │  │
│  │  │ Rule Engine  │      │ AI Reasoner  │                    │  │
│  │  │   (Fast)     │──────│  (Claude)    │                    │  │
│  │  │ Pattern Match│      │   Intelligent│                    │  │
│  │  └──────────────┘      └──────────────┘                    │  │
│  │         │                      │                            │  │
│  │         └──────┬───────────────┘                            │  │
│  │                ▼                                             │  │
│  │        Agent Selection                                       │  │
│  │   (Best match + confidence)                                 │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                             │                                       │
│                             ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              AGENT REGISTRY                                  │  │
│  │                                                              │  │
│  │  Agents:                    Capability Index:               │  │
│  │  • calculator               • "math" → [calculator]         │  │
│  │  • search                   • "search" → [search]           │  │
│  │  • tavily_search            • "web-search" → [tavily]       │  │
│  │  • data_processor           • "data" → [data_processor]     │  │
│  │  • admin_agent              • "admin" → [admin_agent]       │  │
│  │  • weather (MCP)            • "weather" → [weather]         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                             │                                       │
│                             ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │         EXECUTION ENGINE                                     │  │
│  │  • Retry logic  • Fallback strategies  • Circuit breakers   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   DIRECT     │    │   DIRECT     │    │     MCP      │
│   AGENT      │    │   AGENT      │    │   AGENT      │
│              │    │              │    │              │
│ Calculator   │    │   Search     │    │  Weather     │
│  (Python)    │    │  (Python)    │    │  (Server)    │
└──────────────┘    └──────────────┘    └──────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │     RESULT      │
                    │  {"result": 4}  │
                    └─────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/agent-orchestrator.git
cd agent-orchestrator

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your API keys:
#   - ANTHROPIC_API_KEY (for AI reasoning)
#   - TAVILY_API_KEY (optional, for web search)
```

### Basic Usage

```python
import asyncio
from agent_orchestrator import Orchestrator

async def main():
    # Initialize orchestrator
    orchestrator = Orchestrator(config_path="config/orchestrator.yaml")
    await orchestrator.initialize()

    # Process a calculation request
    result = await orchestrator.process({
        "query": "calculate the sum of 15 and 27",
        "operation": "add",
        "operands": [15, 27]
    })

    print(f"Result: {result['data']['calculator']['result']}")
    # Output: Result: 42

    # Process a search request
    result = await orchestrator.process({
        "query": "search for python tutorials",
        "max_results": 5
    })

    print(f"Found {result['data']['search']['total_count']} results")

    # Real-time web search (requires TAVILY_API_KEY)
    result = await orchestrator.process({
        "query": "latest AI news in 2026",
        "max_results": 5
    })

    if 'tavily_search' in result['data']:
        print(f"Answer: {result['data']['tavily_search']['answer']}")

    # Cleanup
    await orchestrator.cleanup()

# Run
asyncio.run(main())
```

### Run Examples

```bash
# Interactive testing (recommended for getting started!)
python3 test_orchestrator_interactive.py

# Run all example scenarios
python3 example_usage.py

# Run agent selection demonstration
python3 demo_agent_selection_simple.py

# Run multi-agent workflow demonstration
python3 demo_multi_agent.py

# Test Tavily web search agent
python3 test_tavily_agent.py

# Run tests
pytest tests/ -v --cov=agent_orchestrator
```

**💡 Tip**: Start with `test_orchestrator_interactive.py` for an interactive, real-time experience! See [INTERACTIVE_TESTING.md](INTERACTIVE_TESTING.md) for details.

---

## 📋 Features

### Intelligent Agent Routing

The orchestrator uses three reasoning modes to select the best agent:

```
┌────────────────────────────────────────────────────────────┐
│               REASONING MODES                              │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  1. RULE-BASED (Fast, Deterministic)                      │
│     ┌──────────────────────────────────────┐             │
│     │ Pattern: "calculate" + "operation"   │             │
│     │ → Agent: calculator                   │             │
│     │ Confidence: 0.9                       │             │
│     │ Time: ~5ms                            │             │
│     └──────────────────────────────────────┘             │
│                                                            │
│  2. AI-BASED (Intelligent, Context-Aware)                 │
│     ┌──────────────────────────────────────┐             │
│     │ Claude analyzes:                      │             │
│     │ • User request                        │             │
│     │ • All agent capabilities              │             │
│     │ • Agent descriptions                  │             │
│     │ → Selects best match                 │             │
│     │ Time: ~800ms                          │             │
│     └──────────────────────────────────────┘             │
│                                                            │
│  3. HYBRID ⭐ (Best of Both)                              │
│     ┌──────────────────────────────────────┐             │
│     │ Step 1: Try rules first (fast)       │             │
│     │ Step 2: If no match → use AI         │             │
│     │ Step 3: Fallback chain if failure    │             │
│     │ Result: Fast + Intelligent           │             │
│     └──────────────────────────────────────┘             │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Agent Types

#### 1. Direct Agents (Python Functions)

Wrap Python functions as agents:

```python
# examples/sample_calculator.py
def calculate(operation: str, operands: List[float]) -> Dict:
    """Perform mathematical calculations."""
    if operation == "add":
        result = sum(operands)
    # ... more operations
    return {"result": result}
```

**Configuration:**
```yaml
- name: "calculator"
  type: "direct"
  direct_tool:
    module: "examples.sample_calculator"
    function: "calculate"
    is_async: false
  capabilities:
    - "math"
    - "calculation"
    - "arithmetic"
```

#### 2. MCP Agents (Protocol Servers)

Connect to MCP (Model Context Protocol) servers:

```python
# examples/sample_weather_server.py
from fastmcp import FastMCP

mcp = FastMCP("Weather Service")

@mcp.tool()
async def get_weather(city: str, units: str = "fahrenheit"):
    """Get weather information for a city."""
    return {"city": city, "temperature": 72, "condition": "Sunny"}

mcp.run(transport="stdio")
```

**Configuration:**
```yaml
- name: "weather"
  type: "mcp"
  connection:
    url: "stdio"
  capabilities:
    - "weather"
    - "forecast"
```

### Security & Governance

```
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 1: INPUT VALIDATION                                  │
│  ┌───────────────────────────────────────────────┐         │
│  │ • Command injection prevention                │         │
│  │ • SQL injection detection                     │         │
│  │ • Path traversal protection                   │         │
│  │ • Size limits and sanitization                │         │
│  └───────────────────────────────────────────────┘         │
│                                                             │
│  Layer 2: ROLE-BASED ACCESS CONTROL                        │
│  ┌───────────────────────────────────────────────┐         │
│  │ • Read-only operations (no approval)          │         │
│  │ • Privileged operations (requires approval)   │         │
│  │ • Allowed/denied operations per agent         │         │
│  │ • Justification requirements                  │         │
│  └───────────────────────────────────────────────┘         │
│                                                             │
│  Layer 3: EXECUTION CONSTRAINTS                             │
│  ┌───────────────────────────────────────────────┐         │
│  │ • Timeout enforcement                         │         │
│  │ • Rate limiting                               │         │
│  │ • Resource constraints                        │         │
│  │ • Circuit breakers                            │         │
│  └───────────────────────────────────────────────┘         │
│                                                             │
│  Layer 4: AUDIT & MONITORING                                │
│  ┌───────────────────────────────────────────────┐         │
│  │ • All operations logged                       │         │
│  │ • Performance metrics tracked                 │         │
│  │ • Health monitoring                           │         │
│  │ • Execution history                           │         │
│  └───────────────────────────────────────────────┘         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Performance & Resilience

- **Async/Await**: Non-blocking I/O for all operations
- **Parallel Execution**: Run independent agents concurrently
- **Circuit Breakers**: Prevent cascading failures
- **Retry Logic**: Automatic retries with exponential backoff
- **Fallback Strategies**: Alternative agents on failure
- **Health Checks**: Monitor agent availability

---

## 📖 Configuration

### Orchestrator Configuration

`config/orchestrator.yaml`:

```yaml
orchestrator:
  name: "main-orchestrator"
  reasoning_mode: "hybrid"  # rule, ai, or hybrid
  ai_provider: "anthropic"  # anthropic or bedrock
  ai_model: "claude-sonnet-4-5-20250929"
  max_parallel_agents: 3
  default_timeout: 30
  retry_attempts: 3

  # AWS Bedrock configuration (optional)
  bedrock:
    model_id: "anthropic.claude-v3-sonnet"
    region: "us-east-1"
    role_arn: "arn:aws:iam::123456789:role/BedrockRole"

validation:
  schema_name: null
  strict: false

retry_config:
  max_attempts: 3
  initial_delay: 1
  max_delay: 10
  exponential_base: 2

enable_metrics: true
enable_audit_log: true
log_level: "INFO"
```

### Agent Configuration

`config/agents.yaml`:

```yaml
agents:
  - name: "calculator"
    type: "direct"
    enabled: true

    direct_tool:
      module: "examples.sample_calculator"
      function: "calculate"
      is_async: false

    capabilities:
      - "math"
      - "calculation"
      - "arithmetic"

    role:
      name: "math-processor"
      description: "Performs mathematical calculations"
      allowed_operations: ["add", "subtract", "multiply", "divide"]
      denied_operations: ["exec", "eval"]
      max_execution_time: 5
      require_approval: false

    constraints:
      max_retries: 2
      timeout: 5
      rate_limit: 60  # requests per minute

    metadata:
      description: "Safe mathematical calculator"
      version: "1.0.0"
```

### Routing Rules

`config/rules.yaml`:

```yaml
rules:
  - name: "calculation_rule"
    priority: 100
    conditions:
      - type: "keyword"
        field: "query"
        value: ["calculate", "compute", "add", "subtract"]
      - type: "field_exists"
        field: "operation"
    actions:
      - type: "route"
        target_agents: ["calculator"]
        confidence: 0.9

  - name: "search_rule"
    priority: 90
    conditions:
      - type: "keyword"
        field: "query"
        value: ["search", "find", "query"]
    actions:
      - type: "route"
        target_agents: ["search"]
        confidence: 0.85
```

---

## 🎨 Available Agents

The framework includes several sample agents:

| Agent | Type | Capabilities | Description |
|-------|------|-------------|-------------|
| **calculator** | Direct | math, calculation, arithmetic | Mathematical operations with input validation |
| **search** | Direct | search, retrieval, query | Document search with safe search enabled |
| **data_processor** | Direct | data, transform, json | Data processing and transformation |
| **admin_agent** | Direct | admin, system, monitoring | Administrative operations (disabled by default) |
| **weather** | MCP | weather, forecast, climate | Weather information via MCP server (disabled) |

### Creating Custom Agents

#### Direct Agent Example:

```python
# my_custom_agent.py
def my_function(param1: str, param2: int) -> dict:
    """My custom agent function."""
    result = f"Processed {param1} with {param2}"
    return {"output": result}
```

Add to `config/agents.yaml`:

```yaml
- name: "my_agent"
  type: "direct"
  direct_tool:
    module: "my_custom_agent"
    function: "my_function"
    is_async: false
  capabilities:
    - "custom_capability"
  enabled: true
```

#### MCP Agent Example:

```python
# my_mcp_server.py
from fastmcp import FastMCP

mcp = FastMCP("My Service")

@mcp.tool()
async def my_tool(input: str) -> dict:
    """My custom MCP tool."""
    return {"result": f"Processed: {input}"}

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

Add to `config/agents.yaml`:

```yaml
- name: "my_mcp_agent"
  type: "mcp"
  connection:
    url: "stdio"
  capabilities:
    - "my_capability"
  enabled: true
```

---

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=agent_orchestrator --cov-report=html

# Run specific test file
pytest tests/test_orchestrator.py -v

# Run specific test
pytest tests/test_security.py::TestInputValidation::test_validate_input_safe_data -v
```

### Test Coverage

Current coverage: **65%**

| Module | Coverage | Status |
|--------|----------|--------|
| orchestrator.py | 71% | ✅ Good |
| security.py | 93% | ✅ Excellent |
| bedrock_reasoner.py | 96% | ✅ Excellent |
| config/models.py | 97% | ✅ Excellent |
| rule_engine.py | 75% | ✅ Good |
| schema_validator.py | 78% | ✅ Good |

See [TEST_COVERAGE_SUMMARY.md](TEST_COVERAGE_SUMMARY.md) for details.

---

## 📊 Monitoring & Observability

### Get Statistics

```python
stats = orchestrator.get_stats()

# Output:
{
    "name": "main-orchestrator",
    "request_count": 152,
    "agents": {
        "total_agents": 3,
        "capabilities": ["math", "search", "data"],
        "agents": [
            {
                "name": "calculator",
                "call_count": 85,
                "success_rate": 0.988,
                "avg_execution_time": 0.125,
                "is_healthy": True
            }
        ]
    },
    "reasoning": {
        "mode": "hybrid",
        "rule_matches": 98,
        "ai_calls": 54
    }
}
```

### Health Checks

```python
# Check all agents
health = await orchestrator.agent_registry.health_check_all()

# Output:
{
    "calculator": True,
    "search": True,
    "data_processor": True
}
```

---

## 🔧 Advanced Usage

### Multi-Agent Workflows

The orchestrator can **automatically distribute a single request across multiple agents** and consolidate their outputs:

#### Example 1: Sequential Multi-Agent

```python
# Request requiring multiple agents in sequence
result = await orchestrator.process({
    "query": "Find AI research papers and calculate their sentiment scores"
})

# Orchestrator automatically:
# 1. Analyzes request → needs search + data processing
# 2. Executes: search agent → data_processor agent (sequential)
# 3. Consolidates outputs into unified response

print(result['_metadata']['agent_trail'])
# Output: ['search', 'data_processor']

print(result['data']['search']['total_count'])
# Output: 10 papers found

print(result['data']['data_processor']['average_sentiment'])
# Output: 0.75 (positive sentiment)
```

#### Example 2: Parallel Multi-Agent

```python
# Request with independent operations
result = await orchestrator.process({
    "query": "Get weather for Tokyo and calculate 15 + 27"
})

# Orchestrator automatically:
# 1. Analyzes request → needs weather + calculator
# 2. Executes: weather agent || calculator agent (parallel!)
# 3. Total time = max(weather_time, calculator_time)

print(result['_metadata']['parallel'])
# Output: True

print(result['data']['weather']['temperature'])
# Output: 20°C

print(result['data']['calculator']['result'])
# Output: 42
```

#### Example 3: Complex Multi-Step

```python
# Request requiring 3+ agents
result = await orchestrator.process({
    "query": "Search tutorials, filter rating > 4.5, calculate average"
})

# Orchestrator automatically:
# 1. search agent → find tutorials
# 2. data_processor agent → filter by rating
# 3. calculator agent → calculate average
# All outputs consolidated in result['data']

print(result['_metadata']['agent_trail'])
# Output: ['search', 'data_processor', 'calculator']
```

**See [MULTI_AGENT_CONFIRMATION.md](MULTI_AGENT_CONFIRMATION.md) for detailed examples.**

### Custom Reasoning Strategy

```python
from agent_orchestrator.reasoning import HybridReasoner

# Custom threshold
reasoner = HybridReasoner(
    rule_engine=rule_engine,
    ai_reasoner=ai_reasoner,
    mode="hybrid",
    rule_confidence_threshold=0.8  # Adjust threshold
)
```

### AWS Bedrock Integration

```yaml
# config/orchestrator.yaml
orchestrator:
  reasoning_mode: "hybrid"
  ai_provider: "bedrock"  # Use AWS Bedrock instead of Anthropic

  bedrock:
    model_id: "anthropic.claude-v3-5-sonnet-20240620-v1:0"
    region: "us-east-1"
    role_arn: "arn:aws:iam::123456789:role/BedrockRole"
    session_name: "orchestrator-session"
```

---

## 📚 Documentation

- **[EVALUATOR_IMPLEMENTATION_SUMMARY.md](EVALUATOR_IMPLEMENTATION_SUMMARY.md)** - Policy evaluator implementation summary ✨ *NEW*
- **[EVALUATORS_GUIDE.md](EVALUATORS_GUIDE.md)** - Complete guide to action evaluators and policy enforcement ✨ *NEW*
- **[CONVERSATIONAL_QUICKSTART.md](CONVERSATIONAL_QUICKSTART.md)** - Quick start guide for conversational features ✨ *NEW*
- **[CONVERSATIONAL_FEATURES.md](CONVERSATIONAL_FEATURES.md)** - Complete conversational UX documentation ✨ *NEW*
- **[AGENT_SELECTION_EXPLAINED.md](AGENT_SELECTION_EXPLAINED.md)** - How agent selection works
- **[MULTI_AGENT_CONFIRMATION.md](MULTI_AGENT_CONFIRMATION.md)** - Multi-agent distribution & consolidation ⭐
- **[NEW_AGENTS_SUMMARY.md](NEW_AGENTS_SUMMARY.md)** - Weather & Admin agent documentation
- **[AGENT_SETUP_GUIDE.md](AGENT_SETUP_GUIDE.md)** - Setup guide for new agents
- **[TEST_COVERAGE_SUMMARY.md](TEST_COVERAGE_SUMMARY.md)** - Testing status and metrics
- **[FIXES_SUMMARY.md](FIXES_SUMMARY.md)** - Recent fixes and improvements
- **[CONFIRMATION_SUMMARY.md](CONFIRMATION_SUMMARY.md)** - Registry & selection confirmation

---

## 🛣️ Roadmap

### Current Version: 1.0.0

- ✅ Core orchestration engine
- ✅ Hybrid reasoning (rule + AI)
- ✅ Direct and MCP agents
- ✅ Security validation
- ✅ AWS Bedrock support
- ✅ Comprehensive testing (65% coverage)

### Planned Features

- [ ] **Enhanced Reasoning**
  - Learning from past decisions
  - Confidence score improvements
  - Multi-model support (GPT-4, Gemini)

- [ ] **Additional Agent Types**
  - REST API agents
  - gRPC service agents
  - Lambda function agents

- [ ] **Improved Observability**
  - Prometheus metrics export
  - Distributed tracing (OpenTelemetry)
  - Real-time dashboards

- [ ] **Advanced Features**
  - Agent versioning and rollback
  - A/B testing framework
  - Cost optimization strategies
  - Hot-reloading of configuration

- [ ] **Developer Experience**
  - CLI tool for agent management
  - Web UI for monitoring
  - Agent marketplace
  - VS Code extension

---

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest tests/ -v`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run linting
flake8 agent_orchestrator/
black agent_orchestrator/

# Run type checking
mypy agent_orchestrator/
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **FastMCP** - MCP protocol implementation
- **Anthropic Claude** - AI reasoning engine
- **AWS Bedrock** - Alternative AI provider
- **pytest** - Testing framework

---

## 📞 Support

- **Documentation**: [Full documentation](docs/)
- **Issues**: [GitHub Issues](https://github.com/yourusername/agent-orchestrator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/agent-orchestrator/discussions)

---

## 🌟 Star History

If you find this project useful, please consider giving it a star! ⭐

---

**Built with ❤️ by the Agent Orchestrator Team**

*Empowering intelligent multi-agent systems*
