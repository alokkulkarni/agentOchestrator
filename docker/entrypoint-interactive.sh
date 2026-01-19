#!/bin/bash
# Entrypoint script for interactive test container

set -e

echo "========================================="
echo "Agent Orchestrator - Interactive Test"
echo "========================================="
echo ""

# Wait for gateway to be ready
echo "Waiting for Model Gateway to be ready..."
/usr/local/bin/wait-for-it.sh model-gateway:8585 --timeout=60

echo "Model Gateway is ready!"
echo ""

# Check if config exists
if [ ! -f "/app/config/orchestrator.yaml" ]; then
    echo "ERROR: Configuration file not found at /app/config/orchestrator.yaml"
    exit 1
fi

# Test gateway connection
echo "Testing gateway connection..."
if curl -f -s http://model-gateway:8585/ > /dev/null 2>&1; then
    echo "✅ Gateway connection successful"
else
    echo "⚠️  Warning: Could not connect to gateway"
fi
echo ""

# Check environment variables
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️  Warning: ANTHROPIC_API_KEY not set"
fi

if [ -z "$GATEWAY_ANTHROPIC_API_KEY" ]; then
    echo "⚠️  Warning: GATEWAY_ANTHROPIC_API_KEY not set"
fi

echo ""
echo "Starting interactive test..."
echo "========================================="
echo ""

# Run the interactive test
exec python3 test_orchestrator_interactive.py
