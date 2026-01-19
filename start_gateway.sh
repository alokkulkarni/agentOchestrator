#!/bin/bash
# Start Model Gateway with environment variables loaded

set -e

echo "Starting Model Gateway..."
echo ""

# Check if .env exists
if [ -f "model_gateway/.env" ]; then
    echo "✅ Found model_gateway/.env"

    # Check if GATEWAY_ANTHROPIC_API_KEY is set
    if grep -q "GATEWAY_ANTHROPIC_API_KEY=" model_gateway/.env | grep -v "your-anthropic-api-key-here"; then
        echo "✅ GATEWAY_ANTHROPIC_API_KEY is configured"
    else
        echo "⚠️  Warning: GATEWAY_ANTHROPIC_API_KEY may not be configured"
    fi
else
    echo "⚠️  Warning: model_gateway/.env not found"
    echo "   The gateway will use environment variables or defaults"
fi

echo ""
echo "Starting gateway on port 8585..."
echo "Press Ctrl+C to stop"
echo ""

# Start the gateway
python3 -m model_gateway.server
