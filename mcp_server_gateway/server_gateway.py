
import asyncio
import logging
import os
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from .registry import ServerRegistry, MCPServerConnection
from .config.loader import load_server_configs
from agent_orchestrator.reasoning import AIReasoner, GatewayReasoner

logger = logging.getLogger(__name__)

class ServerGateway:
    """
    MCP Server Gateway.
    
    Acts as the central coordinator for MCP servers. It uses an AI Reasoner 
    (connecting via Model Gateway) to plan and route requests to the appropriate 
    MCP servers.
    """
    
    def __init__(self, config_path: str, gateway_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize the Gateway.
        
        Args:
            config_path: Path to mcp_servers.yaml
            gateway_url: URL of the Model Gateway (preferred)
            api_key: Anthropic API Key (fallback for direct AIReasoner)
        """
        self.config_path = config_path
        self.gateway_url = gateway_url or os.getenv("MODEL_GATEWAY_URL")
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        
        self.registry = ServerRegistry()
        self._initialized = False

        # Initialize Reasoner
        if self.gateway_url:
            logger.info(f"Using GatewayReasoner connected to {self.gateway_url}")
            self.reasoner = GatewayReasoner(gateway_url=self.gateway_url, api_key=self.api_key)
        elif self.api_key:
            logger.info("Using Direct AIReasoner (Anthropic)")
            self.reasoner = AIReasoner(api_key=self.api_key)
        else:
            raise ValueError("Either MODEL_GATEWAY_URL or ANTHROPIC_API_KEY is required for ServerGateway")

    async def initialize(self):
        """Load configuration and connect to servers."""
        if self._initialized: 
            return
            
        logger.info(f"Loading servers from {self.config_path}")
        configs = load_server_configs(self.config_path)
        
        results = []
        for config in configs:
            if config.enabled:
                try:
                    await self.registry.register(config)
                    logger.info(f"Registered MCP Server: {config.name}")
                except Exception as e:
                    logger.error(f"Failed to register {config.name}: {e}")
        
        self._initialized = True
        logger.info(f"Gateway initialized with {len(self.registry.servers)} servers.")

    async def process_request(self, user_input: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a user request through the gateway.
        """
        if not self._initialized:
            await self.initialize()

        # Get list of connected servers (duck-typed as BaseAgents)
        available_servers = list(self.registry.list_servers().values())
        
        plan = None
        try:
            if isinstance(self.reasoner, GatewayReasoner):
                # GatewayReasoner signature: async reason(query, capabilities, context)
                plan = await self.reasoner.reason(
                    query=user_input, 
                    agent_capabilities=available_servers, # duck-typed
                    context=user_context
                )
            else:
                # AIReasoner signature
                input_data = {
                    "query": user_input,
                    "context": user_context or {}
                }
                plan = await self.reasoner.reason(input_data, available_servers)
                
        except Exception as e:
            logger.error(f"Reasoning failed: {e}")
            return {"success": False, "error": f"Reasoning failed: {str(e)}"}
        
        if not plan:
            return {
                "success": False, 
                "error": "No plan generated",
                "response": "I wasn't able to determine which tools to use for your request."
            }

        logger.info(f"Execution Plan: {plan.agents}")
        
        # 3. Execute Plan
        results = {}
        agent_counts = {}
        
        for agent_name in plan.agents:
            # Handle multiple calls to same agent
            count = agent_counts.get(agent_name, 0) + 1
            agent_counts[agent_name] = count
            
            # Resolve Parameters
            suffix_key = f"{agent_name}_{count}"
            params = plan.parameters.get(suffix_key)
            if params is None:
                params = plan.parameters.get(agent_name, {})
            
            # Get Server
            server = self.registry.get_server(agent_name)
            if not server:
                logger.error(f"Server {agent_name} not found in registry")
                results[agent_name] = {"error": "Server not found"}
                continue
                
            # Determine Tool
            # If explicit tool strategy is implemented later, use it.
            # For now, default to the first tool or search for match.
            if not server.tools:
                logger.warning(f"Server {server.name} has no tools")
                results[agent_name] = {"error": "No tools available"}
                continue
            
            # Simple heuristic: Use first tool
            # Ideally: Reasoner should specify tool name. 
            # In legacy agent model, Agent Name == Capability.
            tool_name = server.tools[0].name
            
            # Check if params has 'tool_name' override? Unlikely in legacy format.
            
            try:
                logger.info(f"Calling {server.name} tool '{tool_name}' with {params}")
                # Call the tool
                # mcp returns CallToolResult
                mcp_result = await server.call_tool(tool_name, params)
                
                # Extract content
                # mcp_result.content is a list of TextContent or ImageContent
                content_text = ""
                if hasattr(mcp_result, 'content'):
                    for item in mcp_result.content:
                        if hasattr(item, 'text'):
                            content_text += item.text
                        else:
                            content_text += str(item)
                
                results[agent_name] = {
                    "output": content_text,
                    "isError": getattr(mcp_result, 'isError', False)
                }
                
            except Exception as e:
                logger.error(f"Error executing {server.name}: {e}")
                results[agent_name] = {"error": str(e)}

        # 4. Final Response (Synthesis)
        # For this stage, we just return the raw results + plan. 
        # A full implementation would use the LLM to summarize the results.
        
        response_text = "Task completed.\n"
        for agent, res in results.items():
            output = res.get('output', res.get('error', 'Unknown result'))
            response_text += f"\n[{agent}]: {output}"
            
        return {
            "success": True,
            "plan": plan.to_dict(),
            "results": results,
            "response": response_text
        }
        
    async def shutdown(self):
        """Cleanup resources."""
        await self.registry.cleanup()
