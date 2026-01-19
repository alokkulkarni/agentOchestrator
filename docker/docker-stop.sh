#!/bin/bash
# Stop all Docker services

set -e

echo "Stopping Agent Orchestrator Docker Services..."
echo ""

# Stop services
docker-compose down

echo ""
echo "========================================="
echo "Services stopped!"
echo "========================================="
echo ""
echo "To remove volumes as well:"
echo "  docker-compose down -v"
echo ""
echo "To remove images:"
echo "  docker-compose down --rmi all"
