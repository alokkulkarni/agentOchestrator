# Weather Agent Setup Guide

## ✅ Weather Agent Now Available!

I've added a new direct weather agent that works immediately with mock data (no API key required for testing).

---

## 🚀 Quick Start (No API Key Needed)

The weather agent now works out of the box with mock data!

```bash
# Just restart the orchestrator
pkill -f agent_orchestrator.server
python3 -m agent_orchestrator.server
```

Now test it:
```bash
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "what is the weather in Glasgow, Scotland", "stream": false}'
```

**Result:** You'll get mock weather data showing ~12°C, partly cloudy conditions.

---

## 🌟 Get Real Weather Data (Optional)

For real weather data, get a free OpenWeatherMap API key:

### Step 1: Get API Key
1. Go to https://openweathermap.org/api
2. Sign up for free (1000 calls/day, no credit card)
3. Get your API key from the dashboard

### Step 2: Set Environment Variable
```bash
export OPENWEATHER_API_KEY="your-api-key-here"
```

### Step 3: Restart Orchestrator
```bash
pkill -f agent_orchestrator.server
python3 -m agent_orchestrator.server
```

Now queries will return real weather data! 🎉

---

## 📋 What Changed

### New Files Created:
- **`examples/sample_weather.py`** - Weather agent implementation
  - Uses OpenWeatherMap API (if key provided)
  - Falls back to mock data (if no key)
  - Supports current weather + 5-day forecast

### Updated Files:
- **`config/agents.yaml`** - Added weather agent configuration (line 320-372)
  - Name: `weather`
  - Type: `direct`
  - Capabilities: `weather`, `forecast`, `climate`, `temperature`, `conditions`
  - Status: **ENABLED** ✅
  - Fallback: `tavily_search` (if weather agent fails)

---

## 🧪 Test the Weather Agent

### Test 1: Current Weather
```bash
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "what is the weather in Glasgow, Scotland", "stream": false}'
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "weather": {
      "location": {
        "name": "Glasgow",
        "country": "GB"
      },
      "current": {
        "temp": 12,
        "feels_like": 10,
        "description": "partly cloudy",
        "humidity": 75,
        "wind_speed": 5.2
      },
      "units": "metric",
      "unit_symbol": "°C"
    }
  }
}
```

### Test 2: Weather Tomorrow
```bash
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "weather in London tomorrow", "stream": false}'
```

### Test 3: Multiple Cities
```bash
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "compare weather in Paris and Berlin", "stream": false}'
```

---

## 🎯 Agent Selection Logic

The orchestrator will now intelligently select the weather agent:

| Query Type | Agent Selected | Reason |
|------------|----------------|--------|
| "weather in Glasgow" | `weather` | Direct weather capability match |
| "what's the temperature" | `weather` | Temperature capability |
| "will it rain tomorrow" | `weather` | Forecast capability |
| "Glasgow weather forecast" | `weather` | Weather + forecast capabilities |

**Fallback:** If the weather agent fails, it automatically tries `tavily_search` (if TAVILY_API_KEY is set).

---

## 🔍 Why Tavily Returned 0 Results

Your original query selected `tavily_search` because:
1. The weather agent was **disabled** (no MCP server)
2. AI reasoner correctly chose `tavily_search` as alternative
3. But `TAVILY_API_KEY` was not set → 0 results

**Now:** The weather agent is **enabled** and will be selected first! ✅

---

## 📊 Comparison: Weather Data Sources

| Feature | Mock Data | OpenWeatherMap API | Tavily Search |
|---------|-----------|-------------------|---------------|
| Setup | None | Free API key | Paid API key |
| Speed | Instant | ~1s | ~2-3s |
| Accuracy | Generic | Real-time | Real-time |
| Forecast | Static | 5-day | Limited |
| Coverage | Any location | Worldwide | Depends on results |
| Cost | Free | 1000/day free | Paid tiers |

---

## ⚙️ Configuration Options

The weather agent accepts these parameters:

```python
{
  "location": "Glasgow, Scotland",    # City name, can include country
  "units": "metric",                  # "metric" (°C), "imperial" (°F), "standard" (K)
  "include_forecast": false           # Include 5-day forecast
}
```

The orchestrator will automatically extract location from queries like:
- "weather in Glasgow"
- "what's the temperature in London"
- "will it rain in Paris tomorrow"

---

## 🐛 Troubleshooting

### Problem: Weather agent not being selected

**Check logs for:**
```
Registered agent: weather
```

If not present:
```bash
# Restart orchestrator
pkill -f agent_orchestrator.server
python3 -m agent_orchestrator.server
```

### Problem: Want real data instead of mock

**Solution:** Set the API key
```bash
export OPENWEATHER_API_KEY="your-key"
python3 -m agent_orchestrator.server
```

### Problem: Still getting tavily_search

**Solution:** The AI may still select tavily_search if your query is more about "searching for weather info" rather than "getting current weather". Try more direct queries:
- ✅ "weather in Glasgow"
- ✅ "temperature in London"
- ❌ "find weather information for Glasgow" (might trigger search)

---

## 📚 API Reference

### Weather Agent Response Format

```json
{
  "success": true,
  "location": {
    "name": "Glasgow",
    "country": "GB",
    "coord": {"lat": 55.86, "lon": -4.26},
    "timezone": 0
  },
  "current": {
    "temp": 12,
    "feels_like": 10,
    "temp_min": 9,
    "temp_max": 14,
    "humidity": 75,
    "pressure": 1013,
    "description": "partly cloudy",
    "main": "Clouds",
    "wind_speed": 5.2,
    "wind_deg": 180,
    "clouds": 40,
    "visibility": 10000
  },
  "forecast": [  // If include_forecast=true
    {
      "time": "2026-01-20 15:00:00",
      "temp": 13,
      "description": "light rain",
      "humidity": 80,
      "wind_speed": 6.0,
      "pop": 65  // Probability of precipitation (%)
    }
  ],
  "units": "metric",
  "unit_symbol": "°C",
  "timestamp": "2026-01-20T12:00:00",
  "note": "Using mock data - set OPENWEATHER_API_KEY for real data"  // Only if using mock
}
```

---

## 🎉 Summary

**Before:**
- ❌ Weather agent disabled (required MCP server)
- ❌ Tavily search selected but no API key → 0 results
- ❌ No way to get weather data

**After:**
- ✅ Weather agent **enabled** and works immediately
- ✅ Uses mock data by default (no setup needed)
- ✅ Optionally use real data with free API key
- ✅ Intelligent agent selection
- ✅ Automatic fallback to tavily_search if needed

**Try it now!** Restart the orchestrator and ask about weather in any city! 🌤️
