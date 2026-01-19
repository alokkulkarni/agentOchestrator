# Environment Variables Setup Guide

## Overview

This guide explains how environment variables are managed in the Agent Orchestrator system. We use a **single API key** that is shared between the Gateway and Orchestrator to avoid duplication.

## Key Principle: Single Source of Truth

✅ **ANTHROPIC_API_KEY** is declared **once** and used by both:
- **Model Gateway** (as `GATEWAY_ANTHROPIC_API_KEY`)
- **Orchestrator** (as `ANTHROPIC_API_KEY`)

This avoids duplication and ensures consistency.

## Environment Files

### `.env.docker` (Template - Safe to Commit)

This is the **template file** with placeholder values. It's safe to commit to git.

```bash
# SHARED API KEYS
ANTHROPIC_API_KEY=your-anthropic-api-key-here
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
# ... other template values
```

**Location**: Project root
**Purpose**: Template for Docker deployment
**Git**: ✅ Committed (no secrets)

### `.env` (Actual Secrets - NOT Committed)

Copy `.env.docker` to `.env` and add your actual API keys.

```bash
# Copy template
cp .env.docker .env

# Edit with actual keys
nano .env
```

**Location**: Project root
**Purpose**: Actual secrets for local/Docker use
**Git**: ❌ Ignored (contains secrets)

### `model_gateway/.env` (Gateway Secrets - NOT Committed)

Gateway-specific environment file for local development.

```bash
GATEWAY_PORT=8585
GATEWAY_ANTHROPIC_API_KEY=your-actual-key-here
```

**Location**: `model_gateway/.env`
**Purpose**: Local gateway development
**Git**: ❌ Ignored (contains secrets)

### `.env.example` and `model_gateway/.env.example` (Templates)

Example templates without secrets.

**Git**: ✅ Committed (no secrets)

## How API Key is Shared

### Docker Deployment

In `docker-compose.yml`, the single `ANTHROPIC_API_KEY` is mapped to both services:

```yaml
services:
  model-gateway:
    environment:
      # Gateway uses ANTHROPIC_API_KEY as GATEWAY_ANTHROPIC_API_KEY
      - GATEWAY_ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}

  orchestrator:
    environment:
      # Orchestrator uses ANTHROPIC_API_KEY directly
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
```

### Local Development

For local development without Docker:

**Gateway** (`model_gateway/.env`):
```bash
GATEWAY_ANTHROPIC_API_KEY=sk-ant-api03-your-key
```

**Orchestrator** (`.env`):
```bash
ANTHROPIC_API_KEY=sk-ant-api03-your-key
```

Both use the **same key value**, just different variable names.

## Setup Instructions

### For Docker Deployment

1. **Copy template**:
   ```bash
   cp .env.docker .env
   ```

2. **Edit .env** with your actual API key:
   ```bash
   nano .env
   ```

   Change:
   ```bash
   ANTHROPIC_API_KEY=your-anthropic-api-key-here
   ```

   To:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here
   ```

3. **Start Docker services**:
   ```bash
   docker-compose up -d
   ```

   Both gateway and orchestrator will use the same API key!

### For Local Development

1. **Setup Gateway**:
   ```bash
   # Copy template
   cp model_gateway/.env.example model_gateway/.env

   # Edit with actual key
   nano model_gateway/.env
   ```

   Set:
   ```bash
   GATEWAY_ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key
   ```

2. **Setup Orchestrator**:
   ```bash
   # Edit root .env
   nano .env
   ```

   Set:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key
   ```

3. **Start services**:
   ```bash
   # Terminal 1: Gateway
   ./start_gateway.sh

   # Terminal 2: Test
   python3 test_orchestrator_interactive.py
   ```

## Environment Variable Hierarchy

### Docker

```
.env (project root)
  ↓
ANTHROPIC_API_KEY
  ↓
  ├─→ Gateway: GATEWAY_ANTHROPIC_API_KEY
  └─→ Orchestrator: ANTHROPIC_API_KEY
```

### Local Development

```
model_gateway/.env          .env (project root)
        ↓                           ↓
GATEWAY_ANTHROPIC_API_KEY    ANTHROPIC_API_KEY
        ↓                           ↓
    Gateway                   Orchestrator
```

## Git Ignore Configuration

The `.gitignore` is configured to:

### ✅ Ignored (NOT Committed - Contains Secrets)
- `.env` (project root)
- `model_gateway/.env`
- `docker/.env`
- Any file matching `*.env` pattern
- `*secret*`, `*SECRET*`, `*.key`, `*.pem`

### ✅ Committed (Templates - No Secrets)
- `.env.docker` (Docker template)
- `.env.example` (General template)
- `model_gateway/.env.example` (Gateway template)

## Verification

### Check Git Status

Verify secrets are ignored:

```bash
# Check what's tracked
git status

# Should NOT see:
# - .env
# - model_gateway/.env

# Should see (if modified):
# - .env.docker (template)
# - .env.example (template)
```

### Verify Environment Loading

**Docker**:
```bash
# Check gateway has the key
docker-compose exec model-gateway env | grep GATEWAY_ANTHROPIC_API_KEY

# Check orchestrator has the key
docker-compose exec orchestrator env | grep ANTHROPIC_API_KEY
```

**Local**:
```bash
# Check gateway .env
grep GATEWAY_ANTHROPIC_API_KEY model_gateway/.env

# Check orchestrator .env
grep ANTHROPIC_API_KEY .env
```

## Best Practices

### ✅ DO:
- Use `.env.docker` as template
- Copy to `.env` and add actual secrets
- Keep same API key value in both locations
- Commit templates (`.env.docker`, `.env.example`)
- Add `.env` files to `.gitignore`

### ❌ DON'T:
- Commit `.env` files with actual secrets
- Hardcode API keys in code
- Put secrets in config YAML files
- Use different API keys for gateway and orchestrator
- Share `.env` files publicly

## Environment Variables Reference

### Shared Variables (declared once in .env)

| Variable | Purpose | Required |
|----------|---------|----------|
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | ✅ Yes |
| `AWS_ACCESS_KEY_ID` | AWS access key (for Bedrock) | ⚠️ If using Bedrock |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key (for Bedrock) | ⚠️ If using Bedrock |
| `AWS_REGION` | AWS region | ⚠️ If using Bedrock |
| `TAVILY_API_KEY` | Tavily search API key | ⚠️ If using Tavily |

### Gateway-Specific (Docker maps from shared)

| Variable | Purpose | Source |
|----------|---------|--------|
| `GATEWAY_ANTHROPIC_API_KEY` | Gateway's Anthropic key | → `${ANTHROPIC_API_KEY}` |
| `GATEWAY_PORT` | Gateway port | Direct |
| `GATEWAY_HOST` | Gateway host | Direct |

### Orchestrator-Specific

| Variable | Purpose | Source |
|----------|---------|--------|
| `ANTHROPIC_API_KEY` | Orchestrator's Anthropic key | Direct |

## Troubleshooting

### Issue: "Anthropic API key is required"

**Check .env exists**:
```bash
ls -la .env
ls -la model_gateway/.env
```

**Check key is set**:
```bash
# Docker
docker-compose config | grep ANTHROPIC_API_KEY

# Local
grep ANTHROPIC_API_KEY .env
grep GATEWAY_ANTHROPIC_API_KEY model_gateway/.env
```

**Solution**: Copy template and add actual key:
```bash
cp .env.docker .env
nano .env  # Add actual key
```

### Issue: Different keys in gateway and orchestrator

**Problem**: Using different API keys wastes credits and causes confusion.

**Solution**: Use the same key in both places:
```bash
# Get the key value
KEY=$(grep ANTHROPIC_API_KEY .env | cut -d= -f2)

# Set it in both locations
echo "ANTHROPIC_API_KEY=$KEY" > .env
echo "GATEWAY_ANTHROPIC_API_KEY=$KEY" >> model_gateway/.env
```

### Issue: .env changes are committed to git

**Problem**: Secrets accidentally committed.

**Check**:
```bash
git status
git diff .env
```

**Solution**: Remove from git tracking:
```bash
# Remove from git (keep local file)
git rm --cached .env
git rm --cached model_gateway/.env

# Commit the removal
git commit -m "Remove .env files from git tracking"
```

## Summary

✅ **Single API Key**: `ANTHROPIC_API_KEY` declared once in `.env`

✅ **Mapped to Services**:
- Gateway: `GATEWAY_ANTHROPIC_API_KEY` ← `ANTHROPIC_API_KEY`
- Orchestrator: `ANTHROPIC_API_KEY` (direct)

✅ **Git Safe**:
- Templates committed (`.env.docker`, `.env.example`)
- Secrets ignored (`.env`, `model_gateway/.env`)

✅ **Easy Setup**:
```bash
# 1. Copy template
cp .env.docker .env

# 2. Add your key
nano .env

# 3. Deploy
docker-compose up -d
```

Your secrets are safe and your configuration is clean! 🔒
