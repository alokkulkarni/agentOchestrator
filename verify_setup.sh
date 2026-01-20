#!/bin/bash
# Verification script to check if all dependencies are installed
# Run this before starting servers to catch any missing dependencies

set -e

echo "========================================"
echo "Verifying Agent Orchestrator Setup"
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}⚠ Warning: Virtual environment not activated${NC}"
    echo "Run: source venv/bin/activate"
    echo ""
fi

echo "Checking Python dependencies..."
echo ""

# Function to check if a module can be imported
check_module() {
    local module=$1
    local display_name=${2:-$module}

    if python3 -c "import $module" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $display_name"
        return 0
    else
        echo -e "${RED}✗${NC} $display_name (missing)"
        return 1
    fi
}

# Track if any modules are missing
MISSING=0

# Core dependencies
echo "Core Dependencies:"
check_module "fastmcp" "fastmcp" || MISSING=1
check_module "anthropic" "anthropic" || MISSING=1
check_module "pydantic" "pydantic" || MISSING=1
check_module "yaml" "pyyaml" || MISSING=1
check_module "dotenv" "python-dotenv" || MISSING=1
echo ""

# API Server dependencies
echo "API Server Dependencies:"
check_module "fastapi" "fastapi" || MISSING=1
check_module "uvicorn" "uvicorn" || MISSING=1
check_module "sse_starlette" "sse-starlette" || MISSING=1
check_module "slowapi" "slowapi" || MISSING=1
echo ""

# Observability dependencies
echo "Observability Dependencies:"
check_module "opentelemetry" "opentelemetry-api" || MISSING=1
check_module "opentelemetry.sdk" "opentelemetry-sdk" || MISSING=1
check_module "opentelemetry.exporter.otlp" "opentelemetry-exporter-otlp" || MISSING=1
check_module "opentelemetry.instrumentation.fastapi" "opentelemetry-instrumentation-fastapi" || MISSING=1
check_module "prometheus_client" "prometheus-client" || MISSING=1
check_module "structlog" "structlog" || MISSING=1
echo ""

# Check if modules can be imported successfully
echo "Checking module imports..."
echo ""

if python3 -c "from model_gateway.observability import init_rate_limiting" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} model_gateway.observability.init_rate_limiting"
else
    echo -e "${RED}✗${NC} model_gateway.observability.init_rate_limiting (import error)"
    MISSING=1
fi

if python3 -c "from agent_orchestrator.orchestrator import Orchestrator" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} agent_orchestrator.orchestrator.Orchestrator"
else
    echo -e "${RED}✗${NC} agent_orchestrator.orchestrator.Orchestrator (import error)"
    MISSING=1
fi

echo ""
echo "Checking environment variables..."
echo ""

if [[ -n "$ANTHROPIC_API_KEY" ]]; then
    echo -e "${GREEN}✓${NC} ANTHROPIC_API_KEY is set"
else
    echo -e "${YELLOW}⚠${NC} ANTHROPIC_API_KEY not set (optional for testing)"
fi

if [[ -n "$TAVILY_API_KEY" ]]; then
    echo -e "${GREEN}✓${NC} TAVILY_API_KEY is set"
else
    echo -e "${YELLOW}⚠${NC} TAVILY_API_KEY not set (optional)"
fi

echo ""
echo "========================================"

if [ $MISSING -eq 0 ]; then
    echo -e "${GREEN}✅ All dependencies installed!${NC}"
    echo ""
    echo "You can now start the servers:"
    echo "  Terminal 1: python3 -m model_gateway.server"
    echo "  Terminal 2: python3 -m agent_orchestrator.server"
    echo ""
    echo "Or use Docker:"
    echo "  docker-compose up -d"
else
    echo -e "${RED}❌ Some dependencies are missing${NC}"
    echo ""
    echo "To fix:"
    echo "  1. Activate virtual environment: source venv/bin/activate"
    echo "  2. Install dependencies: pip install -r requirements.txt"
    echo ""
    echo "Or use Docker (no local install needed):"
    echo "  docker-compose up -d"
    exit 1
fi

echo "========================================"
