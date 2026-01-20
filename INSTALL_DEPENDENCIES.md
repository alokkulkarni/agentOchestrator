# Installing Dependencies

## Issue: Missing Dependencies

If you encounter errors like:
```
ModuleNotFoundError: No module named 'slowapi'
ModuleNotFoundError: No module named 'opentelemetry.instrumentation.fastapi'
```

This is because two dependencies were missing from `requirements.txt`. They have now been added.

## ✅ Fixed: requirements.txt Updated

The following dependencies have been added:
- `slowapi>=0.1.9,<1.0.0` - For rate limiting in Model Gateway
- `opentelemetry-instrumentation-fastapi>=0.48b0,<1.0.0` - For FastAPI tracing in Model Gateway

## 🚀 Installation Options

### Option 1: Use Docker (Recommended - No Local Install Needed)

The easiest way is to use Docker, which handles all dependencies automatically:

```bash
# Start both services with all dependencies installed
docker-compose up -d

# Or with monitoring
docker-compose --profile monitoring up -d
```

**No need to install anything locally!** Everything runs in containers.

### Option 2: Virtual Environment (Recommended for Local Development)

Create a Python virtual environment to avoid system conflicts:

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install all dependencies
pip install -r requirements.txt

# Now you can run the servers
python3 -m model_gateway.server
python3 -m agent_orchestrator.server
```

**To deactivate later:**
```bash
deactivate
```

### Option 3: Install with pipx (For System Python)

If you're using Homebrew Python (macOS) and getting PEP 668 errors:

```bash
# Install pipx if not already installed
brew install pipx

# Use pipx to create an isolated environment
pipx install -e .
```

### Option 4: Override System Protection (Not Recommended)

Only if you understand the risks:

```bash
# Install with --break-system-packages (use with caution)
pip3 install --break-system-packages -r requirements.txt
```

## 📦 What's in requirements.txt

The updated requirements now include:

### Core Dependencies
- `fastmcp>=2.0.0` - FastMCP framework
- `anthropic>=0.42.0` - Claude SDK
- `pydantic>=2.9.0` - Data validation
- `tavily-python>=0.3.0` - Web search

### API Server
- `fastapi>=0.115.0` - Web framework
- `uvicorn>=0.32.0` - ASGI server
- `sse-starlette>=2.1.3` - Server-sent events
- `slowapi>=0.1.9` - ✅ **NEW: Rate limiting**

### Observability
- `opentelemetry-api>=1.27.0` - Distributed tracing
- `opentelemetry-instrumentation-fastapi>=0.48b0` - ✅ **NEW: FastAPI tracing**
- `prometheus-client>=0.21.0` - Metrics
- `structlog>=24.4.0` - Structured logging

## 🧪 Verify Installation

After installing, verify all dependencies are present:

```bash
# Activate your virtual environment first (if using one)
source venv/bin/activate

# Check for slowapi
python3 -c "import slowapi; print(f'slowapi {slowapi.__version__} installed ✓')"

# Check all critical imports
python3 -c "
import fastapi
import uvicorn
import slowapi
import anthropic
import pydantic
print('All critical dependencies installed ✓')
"
```

## 🐳 Why Docker is Easier

Docker eliminates dependency management:
- ✅ All dependencies pre-installed
- ✅ Consistent environment
- ✅ No system conflicts
- ✅ Easy to start/stop services
- ✅ Includes monitoring tools

```bash
# One command to run everything
docker-compose up -d

# Services available at:
# - Model Gateway: http://localhost:8585
# - Orchestrator API: http://localhost:8001
```

## 🔍 Troubleshooting

### Error: "externally-managed-environment"

**Problem:** Python 3.14+ on macOS/Linux prevents system-wide pip installs.

**Solution:** Use a virtual environment (see Option 2 above).

### Error: "No module named 'X'"

**Problem:** Missing dependency in requirements.txt

**Solution:**
1. Update to latest code (requirements.txt is now complete)
2. Reinstall: `pip install -r requirements.txt`
3. Or use Docker: `docker-compose up -d`

### Docker: "port already in use"

**Problem:** Ports 8001 or 8585 are occupied.

**Solution:** Stop the conflicting service or change ports in `docker-compose.yml`:
```yaml
orchestrator-api:
  ports:
    - "8002:8001"  # Map external 8002 to internal 8001
```

## ✅ Quick Start (Recommended Flow)

```bash
# 1. Use Docker (easiest)
docker-compose up -d

# OR if you want local development:

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
export ANTHROPIC_API_KEY="sk-ant-..."
export TAVILY_API_KEY="tvly-..."

# 5. Run servers
python3 -m model_gateway.server  # Terminal 1
python3 -m agent_orchestrator.server  # Terminal 2
```

## 📚 Additional Resources

- [Docker Installation](https://docs.docker.com/get-docker/)
- [Python Virtual Environments](https://docs.python.org/3/library/venv.html)
- [RUNNING_SERVERS.md](RUNNING_SERVERS.md) - Server startup guide
- [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) - Docker deployment guide

---

**Summary:** The missing `slowapi` dependency has been added to `requirements.txt`. Use Docker (easiest) or a virtual environment (for local development) to install all dependencies properly.
