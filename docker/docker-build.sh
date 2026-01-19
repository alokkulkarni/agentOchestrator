#!/bin/bash
# Build all Docker images

set -e

echo "Building Docker images..."
echo ""

# Build Model Gateway
echo "Building Model Gateway..."
docker build -f model_gateway/Dockerfile -t model-gateway:latest .
echo "✅ Model Gateway built"
echo ""

# Build Orchestrator
echo "Building Orchestrator..."
docker build -f Dockerfile -t orchestrator:latest .
echo "✅ Orchestrator built"
echo ""

# Build Interactive Test
echo "Building Interactive Test..."
docker build -f Dockerfile.interactive -t orchestrator-test:latest .
echo "✅ Interactive Test built"
echo ""

echo "All images built successfully!"
echo ""
echo "To start services:"
echo "  docker-compose up -d"
echo ""
echo "To run interactive test:"
echo "  docker-compose --profile interactive up interactive-test"
