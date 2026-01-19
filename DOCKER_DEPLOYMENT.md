# Docker Deployment Guide

## Overview

This guide explains how to deploy the Agent Orchestrator and Model Gateway using Docker containers. The system can be deployed as individual containers or using Docker Compose for orchestration.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                Docker Network                        │
│             (agent-orchestrator-network)             │
│                                                      │
│  ┌──────────────────┐      ┌──────────────────┐   │
│  │  Model Gateway   │      │   Orchestrator   │   │
│  │  (Port 8585)     │◄─────┤   Container      │   │
│  │                  │      │                  │   │
│  │  - Anthropic     │      │  - Agents        │   │
│  │  - Bedrock       │      │  - Rules         │   │
│  └──────────────────┘      │  - Schemas       │   │
│           ▲                 └──────────────────┘   │
│           │                          ▲              │
│           │                          │              │
│  ┌────────┴──────────────────────────┘             │
│  │                                                  │
│  │  ┌──────────────────┐                           │
│  └──┤ Interactive Test │                           │
│     │   Container      │                           │
│     └──────────────────┘                           │
└─────────────────────────────────────────────────────┘
         │
         │ Port Mapping
         ▼
    Host: localhost:8585
```

## Prerequisites

- Docker 20.10+ installed
- Docker Compose 1.29+ installed
- Valid API keys for:
  - Anthropic Claude API
  - AWS credentials (for Bedrock, optional)
  - Tavily API (for web search, optional)

## Quick Start with Docker Compose

### 1. Setup Environment Variables

Copy the template and fill in your API keys:

```bash
cp .env.docker .env
```

Edit `.env` and add your API keys:

```bash
# Required
GATEWAY_ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# Optional (for Bedrock)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
GATEWAY_AWS_REGION=us-east-1

# Optional (for Tavily web search)
TAVILY_API_KEY=your-tavily-key
```

### 2. Build and Start Services

```bash
# Build all images
docker-compose build

# Start core services (gateway + orchestrator)
docker-compose up -d

# View logs
docker-compose logs -f

# Check service health
docker-compose ps
```

### 3. Verify Deployment

```bash
# Check gateway health
curl http://localhost:8585/health

# Check providers
curl http://localhost:8585/providers
```

### 4. Run Interactive Test

```bash
# Start interactive test container
docker-compose --profile interactive up interactive-test

# Or run interactively with shell access
docker-compose run --rm interactive-test /bin/bash
```

## Individual Container Deployment

### Build Individual Images

```bash
# Build Model Gateway
docker build -f model_gateway/Dockerfile -t model-gateway:latest .

# Build Orchestrator
docker build -f Dockerfile -t orchestrator:latest .

# Build Interactive Test
docker build -f Dockerfile.interactive -t orchestrator-test:latest .
```

### Run Model Gateway

```bash
docker run -d \
  --name model-gateway \
  -p 8585:8585 \
  -e GATEWAY_ANTHROPIC_API_KEY="your-key" \
  -e GATEWAY_PORT=8585 \
  -v $(pwd)/model_gateway/config:/app/model_gateway/config:ro \
  model-gateway:latest
```

### Run Orchestrator

```bash
docker run -d \
  --name orchestrator \
  --link model-gateway:model-gateway \
  -e ANTHROPIC_API_KEY="your-key" \
  -e GATEWAY_URL="http://model-gateway:8585" \
  -v $(pwd)/config:/app/config:ro \
  orchestrator:latest
```

### Run Interactive Test

```bash
docker run -it \
  --name interactive-test \
  --link model-gateway:model-gateway \
  -e ANTHROPIC_API_KEY="your-key" \
  -e GATEWAY_URL="http://model-gateway:8585" \
  -v $(pwd)/config:/app/config:ro \
  orchestrator-test:latest
```

## Configuration

### Docker Compose Configuration

The `docker-compose.yml` file defines three services:

1. **model-gateway**: Model Gateway service (port 8585)
2. **orchestrator**: Agent Orchestrator service
3. **interactive-test**: Interactive test container (profile: interactive)

### Environment Variables

#### Model Gateway

| Variable | Description | Default |
|----------|-------------|---------|
| `GATEWAY_HOST` | Server host | 0.0.0.0 |
| `GATEWAY_PORT` | Server port | 8585 |
| `GATEWAY_ANTHROPIC_API_KEY` | Anthropic API key | - |
| `GATEWAY_AWS_REGION` | AWS region | us-east-1 |
| `AWS_ACCESS_KEY_ID` | AWS access key | - |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | - |

#### Orchestrator

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `TAVILY_API_KEY` | Tavily API key | - |
| `GATEWAY_URL` | Gateway URL | http://model-gateway:8585 |

### Volume Mounts

- **Configuration**: `./config` → `/app/config` (read-only)
- **Examples**: `./examples` → `/app/examples` (read-only)
- **Gateway Logs**: Docker volume `gateway-logs`

## Networking

All services communicate through the `agent-orchestrator-network` bridge network:

- **Internal DNS**: Services can reach each other by container name
  - `model-gateway` → Gateway service
  - `orchestrator` → Orchestrator service
- **External Access**: Gateway exposed on host port 8585

## Service Dependencies

Docker Compose handles service dependencies:

```
interactive-test
    ↓ depends_on
orchestrator
    ↓ depends_on (health check)
model-gateway
```

The gateway includes a health check that other services wait for before starting.

## Testing

### Using Docker Compose

```bash
# Run all tests
docker-compose --profile interactive up interactive-test

# Run specific test commands
docker-compose run --rm interactive-test python3 test_gateway.py
docker-compose run --rm interactive-test python3 test_gateway_retry.py
docker-compose run --rm interactive-test python3 test_gateway_fallback.py
```

### Interactive Test Commands

Once in the interactive test container:

```bash
# Calculator tests
/test-all-calc

# Data processor tests
/test-all-dp

# Search test
/search-test

# Multi-agent tests
/multi-parallel
/multi-sequential
```

## Monitoring

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f model-gateway
docker-compose logs -f orchestrator

# Last 100 lines
docker-compose logs --tail=100 model-gateway
```

### Check Service Health

```bash
# Gateway health
curl http://localhost:8585/health | jq

# Container status
docker-compose ps

# Resource usage
docker stats
```

### Gateway Metrics

```bash
# Get provider status
curl http://localhost:8585/providers | jq

# Check fallback logs
docker-compose logs model-gateway | grep -E "⚠️|🔄"
```

## Production Deployment

### Security Best Practices

1. **Environment Variables**:
   ```bash
   # Use Docker secrets for sensitive data
   docker secret create anthropic_api_key ./api_key.txt
   ```

2. **Network Isolation**:
   ```yaml
   # Use internal networks
   networks:
     internal:
       internal: true
     external:
       internal: false
   ```

3. **Read-Only Filesystems**:
   ```yaml
   read_only: true
   tmpfs:
     - /tmp
   ```

4. **Resource Limits**:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 2G
       reservations:
         cpus: '1'
         memory: 1G
   ```

### Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  model-gateway:
    restart: always
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '2'
          memory: 2G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"
```

Run with:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Gateway Won't Start

**Check logs**:
```bash
docker-compose logs model-gateway
```

**Common issues**:
- Missing API key: Set `GATEWAY_ANTHROPIC_API_KEY`
- Port conflict: Change `GATEWAY_PORT` in `.env`
- Health check failing: Increase `start_period` in docker-compose.yml

### Orchestrator Can't Connect to Gateway

**Check network**:
```bash
docker network inspect agent-orchestrator-network
```

**Verify gateway URL**:
```bash
# Inside orchestrator container
docker-compose exec orchestrator curl http://model-gateway:8585/
```

**Fix**: Ensure `GATEWAY_URL` points to `http://model-gateway:8585`

### Interactive Test Exits Immediately

**Issue**: Container exits when no interactive commands

**Fix**: Run with `-it` flags:
```bash
docker-compose run --rm -it interactive-test
```

### Permission Errors

**Issue**: Volume mount permission denied

**Fix**: Ensure proper ownership:
```bash
sudo chown -R $(whoami):$(whoami) ./config
sudo chown -R $(whoami):$(whoami) ./examples
```

## Cleanup

### Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Remove all images
docker-compose down --rmi all
```

### Remove Individual Containers

```bash
docker stop model-gateway orchestrator
docker rm model-gateway orchestrator
docker rmi model-gateway:latest orchestrator:latest
```

## Advanced Usage

### Scale Services

```bash
# Run multiple gateway instances
docker-compose up -d --scale model-gateway=3

# Add load balancer
# (requires additional nginx/haproxy configuration)
```

### Custom Networks

```bash
# Create custom network
docker network create --driver bridge custom-network

# Use in docker-compose.yml
networks:
  default:
    external:
      name: custom-network
```

### Development Mode

Enable hot-reload for development:

```yaml
# docker-compose.dev.yml
services:
  model-gateway:
    volumes:
      - ./model_gateway:/app/model_gateway
    environment:
      - GATEWAY_RELOAD=true
```

Run with:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## CI/CD Integration

### Build Pipeline

```yaml
# .github/workflows/docker.yml
name: Docker Build

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Build images
        run: docker-compose build

      - name: Run tests
        run: docker-compose run --rm interactive-test python3 -m pytest
```

### Container Registry

```bash
# Tag images
docker tag model-gateway:latest myregistry/model-gateway:v1.0
docker tag orchestrator:latest myregistry/orchestrator:v1.0

# Push to registry
docker push myregistry/model-gateway:v1.0
docker push myregistry/orchestrator:v1.0
```

## Summary

✅ **Docker Deployment Features**:
- Individual container support
- Docker Compose orchestration
- Automatic service discovery
- Health checks and dependencies
- Environment-based configuration
- Volume mounts for configs
- Logging and monitoring
- Production-ready setup

The system is now fully containerized and ready for deployment! 🐳
