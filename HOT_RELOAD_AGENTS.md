# 🔥 Hot-Reload Agents Guide

## ✅ Feature: Dynamic Agent Reloading

You can now add, remove, or update agents **without restarting** the orchestrator!

---

## 🚀 How It Works

### Step 1: Update Agent Configuration

Edit `config/agents.yaml` to add/modify/disable agents.

**Example - Adding the Weather Agent:**
```yaml
- name: "weather"
  type: "direct"
  direct_tool:
    module: "examples.sample_weather"
    function: "get_weather"
    is_async: false
  capabilities:
    - "weather"
    - "forecast"
    - "climate"
  enabled: true  # Make sure this is true!
```

### Step 2: Trigger Reload

Call the reload endpoint:
```bash
curl -X POST http://localhost:8001/agents/reload
```

That's it! No restart needed! 🎉

---

## 📋 Reload Endpoint Details

### **POST /agents/reload**

Reloads agent configuration from `config/agents.yaml` without restarting the orchestrator.

**Request:**
```bash
curl -X POST http://localhost:8001/agents/reload
```

**Response:**
```json
{
  "success": true,
  "message": "Agents reloaded successfully",
  "summary": {
    "previous_count": 4,
    "current_count": 5,
    "registered": 5,
    "skipped": 1,
    "failed": 0
  },
  "changes": {
    "added": ["weather"],
    "removed": [],
    "updated": ["calculator", "search", "tavily_search", "data_processor"]
  },
  "agents": {
    "registered": ["calculator", "search", "tavily_search", "data_processor", "weather"],
    "skipped": ["weather_mcp"],
    "failed": []
  }
}
```

---

## 🎯 Use Cases

### 1. Adding New Agents

**Scenario:** You created a new agent and want to test it immediately.

```bash
# 1. Add agent configuration to config/agents.yaml
# 2. Reload agents
curl -X POST http://localhost:8001/agents/reload

# 3. Test immediately
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test my new agent"}'
```

---

### 2. Disabling Problematic Agents

**Scenario:** An agent is causing errors and you want to disable it temporarily.

```bash
# 1. Edit config/agents.yaml and set enabled: false
# 2. Reload
curl -X POST http://localhost:8001/agents/reload

# Agent is now disabled without restart!
```

---

### 3. Updating Agent Configuration

**Scenario:** You want to change agent capabilities or parameters.

```bash
# 1. Update agent config in config/agents.yaml
# 2. Reload
curl -X POST http://localhost:8001/agents/reload

# Changes are live immediately!
```

---

### 4. Development Workflow

**Scenario:** Rapid development and testing of new agents.

```bash
# Edit your agent code
vim examples/my_new_agent.py

# Add to config
vim config/agents.yaml

# Reload (no restart!)
curl -X POST http://localhost:8001/agents/reload

# Test
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'

# Iterate rapidly without restarting!
```

---

## 📊 Response Fields Explained

| Field | Description |
|-------|-------------|
| `success` | Boolean - whether reload succeeded |
| `message` | Human-readable status message |
| `summary.previous_count` | Number of agents before reload |
| `summary.current_count` | Number of agents after reload |
| `summary.registered` | Number of successfully registered agents |
| `summary.skipped` | Number of disabled agents skipped |
| `summary.failed` | Number of agents that failed to register |
| `changes.added` | List of newly added agent names |
| `changes.removed` | List of removed agent names |
| `changes.updated` | List of agent names that were updated |
| `agents.registered` | Full list of registered agent names |
| `agents.skipped` | Full list of skipped agent names |
| `agents.failed` | List of failed agents with error details |

---

## 🔍 Checking Current Agents

Before and after reload, you can check what agents are active:

```bash
# Get current stats
curl http://localhost:8001/stats

# Or health endpoint
curl http://localhost:8001/health
```

---

## ⚠️ Important Notes

### What Gets Reloaded:
- ✅ Agent configurations from `config/agents.yaml`
- ✅ Agent instances (all agents are cleaned up and recreated)
- ✅ Capabilities and metadata
- ✅ Enable/disable state

### What Does NOT Get Reloaded:
- ❌ Orchestrator main configuration (`config/orchestrator.yaml`)
- ❌ Reasoning rules (`config/rules.yaml`)
- ❌ Server settings (port, host, etc.)
- ❌ Environment variables

**For these, you still need to restart the orchestrator.**

---

## 🐛 Troubleshooting

### Problem: Reload fails with error

**Check the response:**
```json
{
  "success": false,
  "error": "Configuration file not found",
  "error_type": "FileNotFoundError"
}
```

**Solutions:**
1. Check that `config/agents.yaml` exists and is valid YAML
2. Check file permissions
3. Check orchestrator logs for details

---

### Problem: Agent shows in "failed" list

**Example Response:**
```json
{
  "agents": {
    "failed": [
      {
        "name": "my_agent",
        "error": "Module 'examples.my_agent' not found"
      }
    ]
  }
}
```

**Solutions:**
1. Check that the agent module exists and is importable
2. Check that the function name is correct
3. Fix the error and reload again

---

### Problem: Old agent still responding

**This shouldn't happen!** Reload completely replaces all agents.

**If it does:**
1. Check the reload response to confirm the agent was registered
2. Check `/stats` to see current agents
3. Try restarting the orchestrator as a last resort

---

## 🎓 Example Workflow: Adding Weather Agent

Let's walk through adding the weather agent from the previous fix:

### 1. Agent Already in Config ✅
The weather agent is already configured in `config/agents.yaml` (lines 320-372).

### 2. Trigger Reload
```bash
curl -X POST http://localhost:8001/agents/reload
```

### 3. Check Response
```json
{
  "success": true,
  "summary": {
    "previous_count": 4,
    "current_count": 5
  },
  "changes": {
    "added": ["weather"]
  }
}
```

### 4. Test Weather Agent
```bash
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "what is the weather in Glasgow, Scotland", "stream": false}'
```

### 5. Verify It Works ✅
```json
{
  "success": true,
  "data": {
    "weather": {
      "location": {"name": "Glasgow"},
      "current": {"temp": 12, "description": "partly cloudy"}
    }
  },
  "metadata": {
    "agent_trail": ["weather"]
  }
}
```

**Done! Weather agent working without any restart!** 🎉

---

## 🔥 Hot-Reload vs Restart

| Feature | Hot-Reload | Restart |
|---------|------------|---------|
| Speed | ~2 seconds | ~5-10 seconds |
| Downtime | None (requests continue) | Yes (brief interruption) |
| Active requests | Continue normally | Interrupted |
| Metrics | Preserved | Reset |
| Sessions | Preserved | Lost |
| Config changes | Agents only | All configs |
| Complexity | Simple API call | Kill + restart process |

**Use hot-reload for:** Agent changes during development and testing

**Use restart for:** Configuration changes, troubleshooting, major updates

---

## 📚 API Documentation

The reload endpoint is also documented in the interactive API docs:

```
http://localhost:8001/docs
```

Look for the **POST /agents/reload** endpoint with full request/response schemas.

---

## ✨ Summary

**Before this feature:**
- ❌ Edit config → restart orchestrator → wait → test
- ❌ Slow development cycle
- ❌ Interrupts active sessions

**After this feature:**
- ✅ Edit config → call API → test immediately
- ✅ Fast development cycle
- ✅ Zero downtime
- ✅ No session interruption

**Try it now!**
```bash
curl -X POST http://localhost:8001/agents/reload
```

Your weather agent is now live! 🌤️
