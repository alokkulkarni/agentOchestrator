
import yaml
import os
from typing import List
from .models import MCPServerConfig

def load_server_configs(config_path: str) -> List[MCPServerConfig]:
    """Load MCP server configurations from YAML file."""
    if not os.path.exists(config_path):
        return []
        
    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)
        
    if not data or 'mcp_servers' not in data:
        return []
        
    configs = []
    for server_data in data['mcp_servers']:
        configs.append(MCPServerConfig(**server_data))
        
    return configs
