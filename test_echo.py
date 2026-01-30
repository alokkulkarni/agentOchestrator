import requests
import time
import sys
import json

GATEWAY_URL = "http://localhost:8666/v1/query"

def test_echo(tool_name, message):
    print(f"\nExample Query: Use {tool_name} to echo '{message}'")
    query = f"Use the {tool_name} tool to echo the message: '{message}'"
    
    payload = {
        "query": query,
        "session_id": "test-session-echo"
    }
    
    try:
        print(f"Sending request to {GATEWAY_URL}...")
        response = requests.post(GATEWAY_URL, json=payload)
        
        if response.status_code != 200:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return

        result = response.json()
        
        print(f"Status: {'✅ Success' if result['success'] else '❌ Failed'}")
        
        if result['success']:
             print(f"Gateway Response: {result.get('formatted_text')}")
             # Check structured results if available
             data = result.get('data', {})
             print(f"Tool Output Data: {json.dumps(data, indent=2)}")
        else:
            print(f"Error Message: {result.get('errors')}")
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        print("Make sure the Gateway is running on port 8666")

if __name__ == "__main__":
    print("=== Testing MCP Gateway Echo Servers ===")
    print("Prerequisites:")
    print("1. mcp_server_gateway/examples/http_server.py running on port 8002")
    print("2. mcp_server_gateway running on port 8666")
    print("3. 'echo_http' and 'echo_stream' configured in mcp_servers.yaml")
    
    # Test 1: HTTP configuration
    test_echo("echo_http", "Testing HTTP Connection")
    
    # Test 2: Streamable HTTP configuration
    test_echo("echo_stream", "Testing Streamable HTTP Connection")
