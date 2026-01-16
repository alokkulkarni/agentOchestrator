# Agent Setup Guide - Weather & Admin

**Quick setup guide for the new Weather and Admin sample agents**

---

## ✅ Admin Agent - Ready to Use

The admin agent is **fully functional** and doesn't require any additional setup.

### Status
- ✅ Module: `examples/sample_admin.py`
- ✅ Functions: 7 (4 read-only, 3 privileged)
- ✅ Testing: All functions verified working
- ✅ Dependencies: None (uses stdlib only)
- ⚠️ Enabled: **False** (disabled by default for security)

### Quick Test
```bash
# Run standalone tests
python3 examples/sample_admin.py

# Expected output:
# ✅ Testing Admin Agent - Read-Only Operations
# ✅ Testing Admin Agent - Privileged Operations
```

### Enable in Orchestrator
1. Edit `config/agents.yaml`
2. Find `admin_agent` section (line 248)
3. Change `enabled: false` to `enabled: true`
4. Restart orchestrator

### Usage Example
```python
from examples.sample_admin import get_system_status, list_users

# Read-only (no approval needed)
status = get_system_status(include_details=True)
print(status['data']['status'])  # "operational"

users = list_users(active_only=True)
print(f"Active users: {users['data']['count']}")

# Privileged (requires approval)
from examples.sample_admin import restart_service

result = restart_service(
    service_name="orchestrator",
    justification="High memory usage"
)
print(f"Requires approval: {result['requires_approval']}")  # True
```

---

## ⚠️ Weather Agent - Requires Setup

The weather MCP server requires FastMCP to be installed.

### Status
- ✅ Module: `examples/sample_weather_server.py`
- ✅ Tools: 5 (get_weather, get_forecast, get_air_quality, get_alerts, list_cities)
- ⚠️ Dependencies: **FastMCP 2.0+ required**
- ⚠️ Enabled: **False** (disabled by default)

### Installation

#### Option 1: Install All Requirements (Recommended)
```bash
# Install all project dependencies including FastMCP
pip install -r requirements.txt
```

#### Option 2: Install Only FastMCP
```bash
# Install just FastMCP for the weather server
pip install "fastmcp>=2.0.0,<3.0.0"
```

### Verify Installation
```bash
# Check if FastMCP is installed
python3 -c "import fastmcp; print(f'FastMCP {fastmcp.__version__} installed')"

# Expected output:
# FastMCP 2.x.x installed
```

### Running the Weather Server

#### Start the Server
```bash
# Start in stdio mode (for local testing)
python3 examples/sample_weather_server.py

# Expected output:
# ============================================================
# Starting Weather Service MCP Server...
# ============================================================
# Available tools:
#   - get_weather(city, units): Get current weather
#   - get_forecast(city, days, units): Get weather forecast
#   - get_air_quality(city): Get air quality index
#   - get_alerts(city): Get weather alerts
#   - list_cities(): List available cities
#
# Available cities:
#   london, new york, paris, san francisco, sydney, tokyo
# ============================================================
```

### Enable in Orchestrator

1. **Install FastMCP** (see above)
2. **Start the weather server** in a separate terminal
3. **Edit `config/agents.yaml`**:
   - Find `weather` agent section (line 194)
   - Change `enabled: false` to `enabled: true`
4. **Restart orchestrator**

### Test the Weather Server

```bash
# Test if server responds (when running)
# In Python:
python3 -c "
from examples.sample_weather_server import get_weather, list_cities
import asyncio

async def test():
    # List available cities
    cities = list_cities()
    print(f'Cities: {cities[\"count\"]}')

    # Get weather
    weather = await get_weather('Tokyo', units='celsius')
    print(f'Tokyo: {weather[\"temperature\"]}°C, {weather[\"condition\"]}')

asyncio.run(test())
"

# Expected output:
# Cities: 6
# Tokyo: 20.0°C, Rainy
```

---

## Configuration Summary

### Current State in `config/agents.yaml`

| Agent | Type | Module | Enabled | Status |
|-------|------|--------|---------|--------|
| calculator | direct | sample_calculator | ✅ True | ✅ Active |
| search | direct | sample_search | ✅ True | ✅ Active |
| data_processor | direct | sample_data_processor | ✅ True | ✅ Active |
| **admin_agent** | direct | **sample_admin** | ❌ False | ⚠️ **New** |
| **weather** | mcp | **sample_weather_server** | ❌ False | ⚠️ **New** |

### To Enable New Agents

```yaml
# config/agents.yaml

# Admin Agent (line 297)
- name: "admin_agent"
  enabled: true  # Change from false to true

# Weather Agent (line 239)
- name: "weather"
  enabled: true  # Change from false to true
```

---

## Troubleshooting

### Admin Agent Issues

**Problem**: Import error when loading admin agent
```
ModuleNotFoundError: No module named 'examples.sample_admin'
```

**Solution**: Make sure you're in the project root directory
```bash
cd /Users/alokkulkarni/Documents/Development/agentOchestrator
python3 -c "from examples.sample_admin import get_system_status"
```

---

### Weather Server Issues

**Problem**: FastMCP not found
```
ModuleNotFoundError: No module named 'fastmcp'
```

**Solution**: Install FastMCP
```bash
pip install "fastmcp>=2.0.0,<3.0.0"
```

**Problem**: Server won't start
```
Error: Transport 'stdio' not available
```

**Solution**: Update FastMCP to latest version
```bash
pip install --upgrade fastmcp
```

**Problem**: Can't connect to weather agent from orchestrator
```
Error: Connection refused to MCP server
```

**Solution**: Make sure weather server is running in a separate terminal
```bash
# Terminal 1: Start weather server
python3 examples/sample_weather_server.py

# Terminal 2: Run orchestrator
python3 example_usage.py
```

---

## Testing Checklist

### Admin Agent Testing

- [ ] Import admin module successfully
- [ ] Call `get_system_status()` - returns operational status
- [ ] Call `list_users()` - returns user list
- [ ] Call `analyze_logs()` - returns log entries
- [ ] Call `generate_report()` - returns report data
- [ ] Call `restart_service()` - returns requires_approval=True
- [ ] Call `update_user_permissions()` - returns requires_approval=True
- [ ] Call `clear_cache()` - session cache doesn't require approval
- [ ] Enable in agents.yaml and restart orchestrator
- [ ] Process request through orchestrator

### Weather Server Testing

- [ ] Install FastMCP
- [ ] Import weather_server module successfully
- [ ] Start weather server (stdio mode)
- [ ] Call `list_cities()` - returns 6 cities
- [ ] Call `get_weather()` - returns weather data
- [ ] Call `get_forecast()` - returns 5-day forecast
- [ ] Call `get_air_quality()` - returns AQI data
- [ ] Call `get_alerts()` - returns alerts (if any)
- [ ] Enable in agents.yaml
- [ ] Process request through orchestrator

---

## Quick Commands Reference

```bash
# Check current directory
pwd
# Should be: /Users/alokkulkarni/Documents/Development/agentOchestrator

# Test admin agent
python3 examples/sample_admin.py

# Install FastMCP
pip install "fastmcp>=2.0.0,<3.0.0"

# Start weather server
python3 examples/sample_weather_server.py

# Run orchestrator examples
python3 example_usage.py

# Check which agents are enabled
grep "enabled:" config/agents.yaml
```

---

## Next Steps

1. **Admin Agent**:
   - ✅ Ready to enable immediately
   - Set `enabled: true` in `config/agents.yaml`
   - Use for system monitoring and administrative tasks

2. **Weather Agent**:
   - ⚠️ Install FastMCP first: `pip install -r requirements.txt`
   - Start server: `python3 examples/sample_weather_server.py`
   - Set `enabled: true` in `config/agents.yaml`
   - Use for weather queries and forecasts

3. **Create Custom Agents**:
   - Follow the sample_admin.py pattern for direct agents
   - Follow the sample_weather_server.py pattern for MCP agents
   - Add configuration to `config/agents.yaml`
   - Enable and test

---

## Support

For detailed documentation, see:
- **NEW_AGENTS_SUMMARY.md** - Comprehensive documentation for both agents
- **FIXES_SUMMARY.md** - Recent fixes and improvements
- **TEST_COVERAGE_SUMMARY.md** - Testing status and coverage metrics
- **README.md** - General orchestrator documentation

---

**Last Updated**: January 5, 2026
**Status**: Admin Agent ✅ Ready | Weather Agent ⚠️ Requires FastMCP
