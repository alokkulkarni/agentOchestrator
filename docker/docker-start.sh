#!/bin/bash
# Start all Docker services

set -e

echo "Starting Agent Orchestrator Docker Services..."
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "   Copying .env.docker to .env..."
    cp .env.docker .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your API keys before continuing!"
    echo ""
    read -p "Press Enter to continue after editing .env, or Ctrl+C to cancel..."
fi

# Start services
echo "Starting services with docker-compose..."
docker-compose up -d

echo ""
echo "Waiting for services to be ready..."
sleep 5

# Check service status
echo ""
docker-compose ps

echo ""
echo "========================================="
echo "Services started!"
echo "========================================="
echo ""
echo "Gateway URL: http://localhost:8585"
echo ""
echo "Check gateway health:"
echo "  curl http://localhost:8585/health"
echo ""
echo "View logs:"
echo "  docker-compose logs -f"
echo ""
echo "Run interactive test:"
echo "  docker-compose --profile interactive up interactive-test"
echo ""
echo "Stop services:"
echo "  docker-compose down"
