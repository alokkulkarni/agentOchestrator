# Local Setup Guide

## Running Services Locally (Without Docker)

This guide explains how to run the Model Gateway and Orchestrator locally on your machine without Docker.

## Prerequisites

- Python 3.11+
- Virtual environment activated
- API keys configured

## Setup

### 1. Install Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 2. Configure Environment Variables

The system looks for environment variables in these locations (in order):

1. **Model Gateway**: `model_gateway/.env`
2. **Orchestrator**: `.env` (project root)

#### Option A: Using .env Files (Recommended)

The `.env` files are already configured with your API keys:

```bash
# Check gateway .env
cat model_gateway/.env | grep GATEWAY_ANTHROPIC_API_KEY

# Check orchestrator .env
cat .env | grep ANTHROPIC_API_KEY
```

#### Option B: Export Environment Variables

If you prefer to export variables manually:

```bash
# For Model Gateway
export GATEWAY_ANTHROPIC_API_KEY="your-key-here"
export GATEWAY_PORT=8585

# For Orchestrator
export ANTHROPIC_API_KEY="your-key-here"
```

## Running Services

### Start Model Gateway

**Option 1: Using helper script (recommended)**
```bash
./start_gateway.sh
```

**Option 2: Direct command**
```bash
python3 -m model_gateway.server
```

**Expected output:**
```
2026-01-19 14:14:50 - model_gateway.server - INFO - Starting Model Gateway...
2026-01-19 14:14:50 - model_gateway.server - INFO - ✅ Initialized Anthropic provider: anthropic
2026-01-19 14:14:50 - model_gateway.server - INFO - ✅ Initialized Bedrock provider: bedrock
2026-01-19 14:14:50 - model_gateway.server - INFO - Gateway started with 2 provider(s)
INFO:     Uvicorn running on http://0.0.0.0:8585 (Press CTRL+C to quit)
```

### Verify Gateway is Running

In another terminal:

```bash
# Check status
curl http://localhost:8585/

# Check health
curl http://localhost:8585/health | python3 -m json.tool

# Check providers
curl http://localhost:8585/providers | python3 -m json.tool
```

### Run Interactive Test

With gateway running in one terminal, start the interactive test in another:

```bash
# Make sure you're in project root
cd /Users/alokkulkarni/Documents/Development/agentOchestrator

# Run interactive test
python3 test_orchestrator_interactive.py
```

## Configuration Files

### Gateway Configuration

**File**: `model_gateway/.env`

```bash
# Server
GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=8585

# API Keys
GATEWAY_ANTHROPIC_API_KEY=your-key-here

# AWS (optional)
GATEWAY_AWS_REGION=us-east-1
```

**File**: `model_gateway/config/gateway.yaml`

```yaml
default_provider: "anthropic"

providers:
  anthropic:
    enabled: true
    default_model: "claude-sonnet-4-5-20250929"

  bedrock:
    enabled: true
    region: "us-east-1"
```

### Orchestrator Configuration

**File**: `.env` (project root)

```bash
# API Key
ANTHROPIC_API_KEY=your-key-here

# Gateway API Key (same as above)
GATEWAY_ANTHROPIC_API_KEY=your-key-here
```

**File**: `config/orchestrator.yaml`

```yaml
orchestrator:
  ai_provider: "gateway"

  gateway:
    url: "http://localhost:8585"
    provider: "anthropic"
```

## Troubleshooting

### Issue: "Anthropic API key is required"

**Symptom:**
```
ERROR - ❌ Failed to initialize provider 'anthropic': Anthropic API key is required
```

**Solution 1: Check .env file**
```bash
cat model_gateway/.env | grep GATEWAY_ANTHROPIC_API_KEY
```

If empty or shows placeholder, edit the file:
```bash
nano model_gateway/.env
# Add: GATEWAY_ANTHROPIC_API_KEY=your-actual-key
```

**Solution 2: Export environment variable**
```bash
export GATEWAY_ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
python3 -m model_gateway.server
```

**Solution 3: Use the helper script**
```bash
./start_gateway.sh
```

### Issue: Port 8585 already in use

**Check what's using the port:**
```bash
lsof -i :8585
```

**Kill the process:**
```bash
kill -9 <PID>
```

**Or change the port:**
```bash
# Edit model_gateway/.env
GATEWAY_PORT=9000

# Then start gateway
python3 -m model_gateway.server
```

### Issue: Gateway loads but only Bedrock initializes

This means Anthropic provider failed to initialize. Usually because:

1. **API key not found**: Check `model_gateway/.env`
2. **API key invalid**: Verify key at console.anthropic.com
3. **Wrong variable name**: Should be `GATEWAY_ANTHROPIC_API_KEY` (with `GATEWAY_` prefix)

**Fix:**
```bash
# Verify the key exists
grep GATEWAY_ANTHROPIC_API_KEY model_gateway/.env

# If missing, add it
echo "GATEWAY_ANTHROPIC_API_KEY=sk-ant-api03-your-key" >> model_gateway/.env

# Restart gateway
python3 -m model_gateway.server
```

### Issue: Orchestrator can't connect to gateway

**Check gateway is running:**
```bash
curl http://localhost:8585/
```

**Check orchestrator config:**
```bash
grep -A 3 "gateway:" config/orchestrator.yaml
```

Should show:
```yaml
gateway:
  url: "http://localhost:8585"
  provider: "anthropic"
```

## Environment Variable Loading

The system loads environment variables in this order:

1. **Pydantic Settings**: Automatically loads from `.env` file
2. **Shell Environment**: Variables exported in terminal
3. **Default Values**: Built-in defaults if not specified

### Gateway (.env file locations checked)

```python
env_file=["model_gateway/.env", ".env"]
```

The gateway checks:
1. `model_gateway/.env` (when running from project root)
2. `.env` (project root, for Docker or alternative setup)

### Orchestrator (.env file location)

```python
env_file=".env"  # Project root
```

## Quick Commands Reference

```bash
# Start gateway
./start_gateway.sh
# OR
python3 -m model_gateway.server

# Check gateway status
curl http://localhost:8585/health

# Run interactive test
python3 test_orchestrator_interactive.py

# Run specific tests
python3 test_gateway.py
python3 test_gateway_retry.py
python3 test_gateway_fallback.py

# View gateway logs
tail -f model_gateway/gateway.log
```

## Workflow Example

**Terminal 1: Start Gateway**
```bash
cd /Users/alokkulkarni/Documents/Development/agentOchestrator
source venv/bin/activate
./start_gateway.sh
```

**Terminal 2: Run Tests**
```bash
cd /Users/alokkulkarni/Documents/Development/agentOchestrator
source venv/bin/activate

# Quick health check
curl http://localhost:8585/health | jq

# Run interactive test
python3 test_orchestrator_interactive.py

# Try commands:
# /test-all-calc
# /test-all-dp
# /multi-parallel
```

## VS Code Setup

If using VS Code, create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Start Gateway",
      "type": "python",
      "request": "launch",
      "module": "model_gateway.server",
      "console": "integratedTerminal",
      "envFile": "${workspaceFolder}/model_gateway/.env"
    },
    {
      "name": "Interactive Test",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/test_orchestrator_interactive.py",
      "console": "integratedTerminal",
      "envFile": "${workspaceFolder}/.env"
    }
  ]
}
```

## Summary

✅ **Quick Start:**
```bash
# 1. Start gateway
./start_gateway.sh

# 2. In another terminal, run test
python3 test_orchestrator_interactive.py
```

✅ **Environment files:**
- Gateway: `model_gateway/.env`
- Orchestrator: `.env` (project root)

✅ **Both files are already configured with your API keys**

✅ **The gateway now loads .env files from both locations automatically**
