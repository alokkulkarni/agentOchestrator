# Installation Guide

## Prerequisites

- **Python 3.11+** (Python 3.14.2 confirmed working)
- **pip** package manager
- **Anthropic API Key** (for AI reasoning features)

## Step-by-Step Installation

### 1. Verify Python Version

```bash
python3 --version
# Should show Python 3.11 or higher
```

### 2. Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# Or install with development dependencies
pip install -e ".[dev]"
```

Expected packages to be installed:
- fastmcp >= 2.0.0
- anthropic >= 0.42.0
- pydantic >= 2.9.0
- pydantic-settings >= 2.6.0
- jsonschema >= 4.23.0
- pyyaml >= 6.0.2
- tenacity >= 9.0.0
- aiohttp >= 3.11.0
- python-dotenv >= 1.0.0

### 3. Set Up Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your Anthropic API key
nano .env  # or use your preferred editor
```

Add to `.env`:
```
ANTHROPIC_API_KEY=your_actual_api_key_here
```

Get your API key from: https://console.anthropic.com/

### 4. Verify Installation

Run the verification script:

```bash
python3 verify_installation.py
```

Or manually test:

```python
# Test 1: Import the package
python3 -c "from agent_orchestrator import Orchestrator; print('✓ Package import successful')"

# Test 2: Test calculator
python3 -c "from examples.sample_calculator import calculate; print(calculate('add', [2, 3]))"

# Test 3: Check configuration loading
python3 -c "from agent_orchestrator.config import load_orchestrator_config; config = load_orchestrator_config('config/orchestrator.yaml'); print(f'✓ Config loaded: {config.name}')"
```

### 5. Run Example

```bash
# Run the example usage script
python3 example_usage.py
```

Expected output:
```
Agent Orchestrator - Example Usage
=================================================================
Example 1: Mathematical Calculation
...
```

### 6. Run Tests

```bash
# Install test dependencies if not already installed
pip install pytest pytest-asyncio pytest-cov pytest-mock

# Run all tests
pytest

# Run with coverage
pytest --cov=agent_orchestrator --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

## Installation Verification Checklist

- [ ] Python 3.11+ installed
- [ ] All dependencies installed (`pip list` shows all required packages)
- [ ] `.env` file created with API key
- [ ] Package imports successfully
- [ ] Sample calculator works
- [ ] Configuration files load correctly
- [ ] Example script runs
- [ ] Tests pass

## Troubleshooting

### Issue: ModuleNotFoundError

```
ModuleNotFoundError: No module named 'yaml'
```

**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: API Key Not Found

```
ConfigurationError: ANTHROPIC_API_KEY not found
```

**Solution**: Set environment variable
```bash
# Option 1: Set in .env file
echo "ANTHROPIC_API_KEY=your_key" >> .env

# Option 2: Export in shell
export ANTHROPIC_API_KEY=your_key

# Option 3: Pass to constructor
orchestrator = Orchestrator(api_key="your_key")
```

### Issue: Import Error for agent_orchestrator

```
ModuleNotFoundError: No module named 'agent_orchestrator'
```

**Solution**: Install in development mode
```bash
pip install -e .
```

### Issue: Configuration File Not Found

```
ConfigurationError: Configuration file not found
```

**Solution**: Run from project root directory
```bash
cd /path/to/agentOchestrator
python3 example_usage.py
```

### Issue: Port Already in Use (MCP Server)

```
OSError: [Errno 48] Address already in use
```

**Solution**: Change port in config or kill existing process
```bash
# Find process using port 8080
lsof -i :8080

# Kill process
kill -9 <PID>

# Or change port in config/agents.yaml
```

## Virtual Environment (Recommended)

It's recommended to use a virtual environment:

```bash
# Create virtual environment
python3 -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# When done
deactivate
```

## Docker Installation (Optional)

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV ANTHROPIC_API_KEY=""

CMD ["python3", "example_usage.py"]
```

Build and run:

```bash
docker build -t agent-orchestrator .
docker run -e ANTHROPIC_API_KEY=your_key agent-orchestrator
```

## Next Steps

After successful installation:

1. Read the [Quick Start Guide](QUICKSTART.md)
2. Review [README.md](README.md) for full documentation
3. Explore sample agents in `examples/`
4. Customize configuration in `config/`
5. Run `python3 example_usage.py` to see it in action

## Support

If you encounter issues:

1. Check this troubleshooting guide
2. Review error messages carefully
3. Ensure all dependencies are installed
4. Verify you're using Python 3.11+
5. Check that configuration files are valid YAML

For additional help, create an issue with:
- Python version
- Operating system
- Full error message
- Steps to reproduce
