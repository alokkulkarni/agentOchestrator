
"""
MCP Server Gateway API Entry Point.

Run with: python3 -m mcp_server_gateway.server
"""

if __name__ == "__main__":
    import uvicorn
    import os
    from pathlib import Path
    from dotenv import load_dotenv

    # Load environment variables
    # 1. Key override: Load local .env (specific config)
    local_env = Path(__file__).parent / ".env"
    if local_env.exists():
        print(f"Loading local env from {local_env}")
        load_dotenv(dotenv_path=local_env, override=True)

    # 2. Load root .env (base config) - do not override existing
    root_env = Path(__file__).parent.parent / ".env"
    load_dotenv(dotenv_path=root_env, override=False)

    host = os.getenv("GATEWAY_API_HOST", "0.0.0.0")
    port = int(os.getenv("GATEWAY_API_PORT", "8001"))
    reload = os.getenv("GATEWAY_API_RELOAD", "false").lower() == "true"
    log_level = os.getenv("GATEWAY_API_LOG_LEVEL", "info").lower()

    print(f"Starting MCP Server Gateway API...")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    
    uvicorn.run(
        "mcp_server_gateway.api.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )
