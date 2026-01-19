# Docker Quick Start Guide

Get the Agent Orchestrator running in Docker in 5 minutes!

## Prerequisites

- Docker installed
- Docker Compose installed
- Anthropic API key

## Quick Start

### 1. Setup Environment

```bash
# Copy environment template
cp .env.docker .env

# Edit .env and add your API key
nano .env
```

Add your Anthropic API key (only needs to be set once):
```bash
# In .env, change this line:
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# To your actual key:
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here
```

**Note**: The same key is automatically used by both Gateway and Orchestrator!

### 2. Build and Start

```bash
# Build all containers
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

### 3. Verify Gateway is Running

```bash
# Check health
curl http://localhost:8585/health

# Expected output:
# {
#   "status": "healthy",
#   "providers": {
#     "anthropic": {"status": "healthy", ...},
#     "bedrock": {"status": "healthy", ...}
#   }
# }
```

### 4. Run Interactive Test

```bash
# Start interactive test container
docker-compose --profile interactive up interactive-test
```

You'll see:
```
=========================================
Agent Orchestrator - Interactive Testing
=========================================

Type your query or use commands:
  /help             - Show all available commands
  /examples         - Show example queries
...
You >
```

### 5. Try Test Commands

Once in the interactive test:

```bash
# Test calculator
You > /calc-add

# Test all calculator operations
You > /test-all-calc

# Test data processor
You > /test-all-dp

# Test multi-agent parallel execution
You > /multi-parallel
```

## Common Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Just gateway
docker-compose logs -f model-gateway

# Last 100 lines
docker-compose logs --tail=100
```

### Stop Services

```bash
# Stop all
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Restart Services

```bash
# Restart gateway
docker-compose restart model-gateway

# Restart all
docker-compose restart
```

## Helper Scripts

We've provided convenient scripts in the `docker/` directory:

```bash
# Build all images
./docker/docker-build.sh

# Start services
./docker/docker-start.sh

# Stop services
./docker/docker-stop.sh

# Check health
./docker/docker-health.sh
```

## Troubleshooting

### Gateway Won't Start

**Check logs:**
```bash
docker-compose logs model-gateway
```

**Common fix:** Verify API key is set:
```bash
docker-compose exec model-gateway env | grep ANTHROPIC
```

### Can't Connect to Gateway

**Test from inside container:**
```bash
docker-compose exec orchestrator curl http://model-gateway:8585/
```

**Common fix:** Ensure services are on same network:
```bash
docker network inspect agent-orchestrator-network
```

### Interactive Test Exits Immediately

**Run with interactive flags:**
```bash
docker-compose run --rm -it interactive-test
```

## Architecture

```
┌─────────────────────────────────────┐
│      Docker Compose Network         │
│   (agent-orchestrator-network)      │
│                                     │
│  ┌─────────────┐  ┌──────────────┐ │
│  │   Gateway   │  │ Orchestrator │ │
│  │  Port 8585  │◄─┤   Service    │ │
│  └─────────────┘  └──────────────┘ │
│         ▲                           │
│         │                           │
│  ┌──────┴─────────┐                │
│  │ Interactive    │                │
│  │     Test       │                │
│  └────────────────┘                │
└─────────────────────────────────────┘
         │
    Exposed Port
         │
    localhost:8585
```

## What's Running

After `docker-compose up -d`:

| Service | Container | Port | Description |
|---------|-----------|------|-------------|
| Model Gateway | `model-gateway` | 8585 | AI provider gateway |
| Orchestrator | `orchestrator` | - | Agent orchestrator |

The interactive test container starts on demand with:
```bash
docker-compose --profile interactive up interactive-test
```

## Next Steps

- Read [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) for advanced configuration
- Check [MODEL_GATEWAY_IMPLEMENTATION.md](MODEL_GATEWAY_IMPLEMENTATION.md) for gateway details
- Review [test_orchestrator_interactive.py](test_orchestrator_interactive.py) for test commands

## Summary

✅ **Quick Start Complete!**

You now have:
- ✅ Model Gateway running on port 8585
- ✅ Orchestrator connected to gateway
- ✅ Interactive test ready to run
- ✅ All services networked together

**Test it:**
```bash
docker-compose --profile interactive up interactive-test
```

Then try: `/test-all-calc` 🚀
