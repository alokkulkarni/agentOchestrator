#!/bin/bash
# Setup script for Agent Orchestrator
# This creates a virtual environment and installs all dependencies

set -e

echo "========================================"
echo "Agent Orchestrator - Environment Setup"
echo "========================================"
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed"
    exit 1
fi

echo "✓ Python version: $(python3 --version)"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

echo ""
echo "📥 Installing dependencies..."
echo ""

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip > /dev/null 2>&1

# Install all dependencies
echo "Installing packages from requirements.txt..."
echo "This may take a few minutes..."
pip install -r requirements.txt

# Verify critical packages
echo ""
echo "Verifying installation..."
python3 -c "import fastapi, uvicorn, slowapi, anthropic, opentelemetry" && echo "✓ All critical packages installed successfully" || echo "⚠ Warning: Some packages may be missing"

echo ""
echo "========================================"
echo "✅ Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Set your API keys:"
echo "   export ANTHROPIC_API_KEY='sk-ant-...'"
echo "   export TAVILY_API_KEY='tvly-...'"
echo ""
echo "3. Run the servers:"
echo "   python3 -m model_gateway.server       # Terminal 1"
echo "   python3 -m agent_orchestrator.server  # Terminal 2"
echo ""
echo "Or use Docker:"
echo "   docker-compose up -d"
echo ""
