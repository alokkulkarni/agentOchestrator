# 🔑 Environment Variables Setup Guide

## ✅ What's Fixed

### 1. Weather Agent Now Works ✅
- Fixed parameter extraction from queries
- Automatically extracts location from natural language
- No more "missing location argument" errors

### 2. .env File Auto-Loading ✅
- Both servers now automatically load .env on startup
- Works in **normal mode** (python3 -m ...)
- Works in **Docker mode** (docker-compose up)
- No need to manually export variables!

---

## 🚀 Quick Setup

### Step 1: Create .env File

```bash
# Copy the template
cp .env.example .env

# Edit with your API keys
vim .env  # or nano, code, etc.
```

### Step 2: Add Your API Keys

**Minimum required:**
```env
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

**Recommended (for all features):**
```env
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
TAVILY_API_KEY=tvly-your-actual-key-here
OPENWEATHER_API_KEY=your-actual-key-here
```

### Step 3: Start Servers

**Normal Mode:**
```bash
# No need to export! Just start the servers
python3 -m model_gateway.server      # Terminal 1
python3 -m agent_orchestrator.server  # Terminal 2
```

**Docker Mode:**
```bash
# No need to export! Just run docker-compose
docker-compose up -d
```

**That's it!** The .env file is automatically loaded! 🎉

---

## 📋 Verification

```bash
# Test weather query
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "what is the weather in Glasgow, Scotland tomorrow", "stream": false}'
```

Should work now! Weather agent extracts "Glasgow, Scotland" automatically! ✅
