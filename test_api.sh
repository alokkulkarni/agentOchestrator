#!/bin/bash
# Quick API test script

set -e

API_URL="${API_URL:-http://localhost:8001}"

echo "🧪 Testing Agent Orchestrator API at $API_URL"
echo "================================================"

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test 1: Root endpoint
echo -e "\n${BLUE}1. Testing root endpoint...${NC}"
curl -s $API_URL/ | jq '.'

# Test 2: Health check
echo -e "\n${BLUE}2. Testing health check...${NC}"
curl -s $API_URL/health | jq '.status, .agents.total'

# Test 3: Non-streaming query
echo -e "\n${BLUE}3. Testing non-streaming query (calculate 15 + 27)...${NC}"
curl -s -X POST $API_URL/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "calculate 15 + 27", "stream": false}' | jq '.success, .data'

# Test 4: Streaming query
echo -e "\n${BLUE}4. Testing streaming query (watch events in real-time)...${NC}"
echo "Press Ctrl+C to stop"
echo ""
curl -N -X POST $API_URL/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "calculate 8 * 12", "stream": true}'

echo -e "\n${GREEN}✅ All tests passed!${NC}"
