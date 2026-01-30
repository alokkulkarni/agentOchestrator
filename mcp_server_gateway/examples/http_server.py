
from fastmcp import FastMCP
import uvicorn

# Create an MCP server
mcp = FastMCP("Remote Echo Server")

@mcp.tool()
def echo_message(message: str) -> str:
    """
    Echo back a message.
    
    Args:
        message: The message to echo
    """
    return f"Echo from Remote Server: {message}"

@mcp.tool()
def http_info() -> str:
    """Return info about this HTTP server."""
    return "Running on HTTP (SSE supported)"

if __name__ == "__main__":
    # fastmcp uses SSE transport by default when run via uvicorn logic often,
    # but here we use mcp.run(transport='sse') which configures starlette app
    # Running directly will start uvicorn
    print("Starting Echo Server on http://localhost:8002")
    mcp.run(transport="sse", port=8002)
