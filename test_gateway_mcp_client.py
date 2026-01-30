
import asyncio
import os
import sys

# Ensure we can find the modules
sys.path.append(os.getcwd())

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_test():
    print("=== Testing Gateway Interface via MCP Client ===")
    
    # Define server parameters - point to our new interface
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server_gateway/interface.py"],
        env={
            **os.environ,
            "PYTHONPATH": os.getcwd(),  # Add current directory to python path
            "PYTHONUNBUFFERED": "1",
            "MODEL_GATEWAY_URL": "http://localhost:8585" # Ensure this is set
        }
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize
                await session.initialize()
                
                # List tools to verify connection
                tools = await session.list_tools()
                print(f"\nConnected to Gateway. Available tools: {[t.name for t in tools.tools]}")
                
                # Test Cases
                test_queries = [
                    "Calculate 50 * 4",
                    "Echo the message 'Hello MCP Client'"
                    # Search might fail if search server isn't running separately? 
                    # No, the gateway registry starts them as subprocesses usually or connects to them
                ]
                
                for query in test_queries:
                    print(f"\n--- Sending Query: '{query}' ---")
                    
                    try:
                        result = await session.call_tool("query_gateway", arguments={"request": query})
                        
                        # MCP returns a list of content items (TextContent, ImageContent, etc)
                        # We just print the text part
                        if result.content:
                            for item in result.content:
                                if hasattr(item, "text"):
                                    print(f"Response: {item.text}")
                                else:
                                    print(f"Response (other type): {item}")
                        else:
                            print("Empty response")
                            
                    except Exception as e:
                        print(f"Query Failed: {e}")
                        
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_test())
