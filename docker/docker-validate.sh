#!/bin/bash
# Validate Docker deployment setup

set -e

echo "========================================="
echo "Docker Deployment Validation"
echo "========================================="
echo ""

ERRORS=0
WARNINGS=0

# Check Docker installation
echo "Checking Docker installation..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo "✅ Docker found: $DOCKER_VERSION"
else
    echo "❌ Docker not found"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Check Docker Compose
echo "Checking Docker Compose..."
if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version)
    echo "✅ Docker Compose found: $COMPOSE_VERSION"
else
    echo "❌ Docker Compose not found"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Check required files
echo "Checking required files..."
FILES=(
    "docker-compose.yml"
    "Dockerfile"
    "model_gateway/Dockerfile"
    "Dockerfile.interactive"
    ".dockerignore"
    "config/orchestrator.yaml"
    "model_gateway/config/gateway.yaml"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file not found"
        ERRORS=$((ERRORS + 1))
    fi
done
echo ""

# Check .env file
echo "Checking environment configuration..."
if [ -f ".env" ]; then
    echo "✅ .env file exists"

    # Check for required variables
    if grep -q "GATEWAY_ANTHROPIC_API_KEY" .env; then
        if grep -q "your-anthropic-api-key-here" .env; then
            echo "⚠️  GATEWAY_ANTHROPIC_API_KEY needs to be configured"
            WARNINGS=$((WARNINGS + 1))
        else
            echo "✅ GATEWAY_ANTHROPIC_API_KEY is set"
        fi
    else
        echo "❌ GATEWAY_ANTHROPIC_API_KEY not found in .env"
        ERRORS=$((ERRORS + 1))
    fi

    if grep -q "ANTHROPIC_API_KEY" .env; then
        if grep -q "your-anthropic-api-key-here" .env; then
            echo "⚠️  ANTHROPIC_API_KEY needs to be configured"
            WARNINGS=$((WARNINGS + 1))
        else
            echo "✅ ANTHROPIC_API_KEY is set"
        fi
    else
        echo "❌ ANTHROPIC_API_KEY not found in .env"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "⚠️  .env file not found (will use .env.docker template)"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# Check Docker scripts
echo "Checking Docker helper scripts..."
SCRIPTS=(
    "docker/wait-for-it.sh"
    "docker/entrypoint-interactive.sh"
    "docker/docker-build.sh"
    "docker/docker-start.sh"
    "docker/docker-stop.sh"
    "docker/docker-health.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        if [ -x "$script" ]; then
            echo "✅ $script (executable)"
        else
            echo "⚠️  $script (not executable)"
            WARNINGS=$((WARNINGS + 1))
        fi
    else
        echo "❌ $script not found"
        ERRORS=$((ERRORS + 1))
    fi
done
echo ""

# Check port availability
echo "Checking port availability..."
if lsof -Pi :8585 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 8585 is already in use"
    WARNINGS=$((WARNINGS + 1))
else
    echo "✅ Port 8585 is available"
fi
echo ""

# Summary
echo "========================================="
echo "Validation Summary"
echo "========================================="
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo "✅ All checks passed!"
    echo ""
    echo "Ready to deploy! Run:"
    echo "  docker-compose up -d"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo "⚠️  $WARNINGS warning(s) found"
    echo ""
    echo "You can proceed, but address warnings for best experience."
    exit 0
else
    echo "❌ $ERRORS error(s) found"
    if [ $WARNINGS -gt 0 ]; then
        echo "⚠️  $WARNINGS warning(s) found"
    fi
    echo ""
    echo "Please fix errors before deploying."
    exit 1
fi
