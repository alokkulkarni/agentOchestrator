#!/bin/bash
# Check health of all Docker services

set -e

echo "========================================="
echo "Agent Orchestrator - Health Check"
echo "========================================="
echo ""

# Check if services are running
echo "Service Status:"
echo "---------------"
docker-compose ps
echo ""

# Check gateway health
echo "Gateway Health Check:"
echo "--------------------"
if curl -f -s http://localhost:8585/health > /dev/null 2>&1; then
    echo "✅ Gateway is healthy"

    # Get detailed health info
    echo ""
    echo "Gateway Health Details:"
    curl -s http://localhost:8585/health | python3 -m json.tool
else
    echo "❌ Gateway is not responding"
fi

echo ""

# Check providers
echo "Gateway Providers:"
echo "------------------"
if curl -f -s http://localhost:8585/providers > /dev/null 2>&1; then
    curl -s http://localhost:8585/providers | python3 -m json.tool
else
    echo "❌ Could not fetch providers"
fi

echo ""
echo "========================================="
