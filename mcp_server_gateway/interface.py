
import asyncio
import os
import logging
import sys
from fastmcp import FastMCP
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("mcp_gateway_interface")

# Initialize FastMCP Server
mcp = FastMCP("Agent Orchestrator Gateway")

# Global Gateway instance
gateway = None

async def get_gateway():
    global gateway
    if gateway is None:
        try:
            # Add project root to path
            sys.path.append(os.getcwd())
            
            from mcp_server_gateway.server_gateway import ServerGateway
            from dotenv import load_dotenv
            
            # Load env vars
            load_dotenv(override=True)
            
            # Determine config path
            root_dir = os.getcwd()
            config_path = os.path.join(root_dir, "mcp_server_gateway/config/mcp_servers.yaml")
            
            gateway_url = os.getenv("MODEL_GATEWAY_URL")
            api_key = os.getenv("ANTHROPIC_API_KEY")
            
            gateway = ServerGateway(config_path, gateway_url=gateway_url, api_key=api_key)
            await gateway.initialize()
            
        except Exception as e:
            logger.error(f"Failed to initialize gateway: {e}")
            raise
        
    return gateway

@mcp.tool()
async def query_gateway(
    request: str, 
    session_id: Optional[str] = None, 
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Process a natural language query through the Agent Orchestrator Gateway.
    
    Args:
        request: The user's natural language query
        session_id: Optional session ID for conversation context
        context: Optional additional context parameters
    """
    try:
        gw = await get_gateway()
        
        result = await gw.process_request(request, context or {})
        
        if result.get("success"):
            return result.get("response", "No response text generation.")
        else:
            return f"Error: {result.get('error', 'Unknown error')}"
            
    except Exception as e:
        return f"System Error: {str(e)}"

if __name__ == "__main__":
    # Explicitly use stdio transport for MCP client compatibility
    mcp.run(transport='stdio')
