"""
Agent Orchestrator API Server Entry Point

This module provides a convenient entry point for running the orchestrator API server.
Run with: python3 -m agent_orchestrator.server

The actual API implementation is in agent_orchestrator.api.server
"""

if __name__ == "__main__":
    import uvicorn
    import os

    # Get configuration from environment
    host = os.getenv("ORCHESTRATOR_API_HOST", "0.0.0.0")
    port = int(os.getenv("ORCHESTRATOR_API_PORT", "8001"))
    reload = os.getenv("ORCHESTRATOR_API_RELOAD", "false").lower() == "true"
    log_level = os.getenv("ORCHESTRATOR_API_LOG_LEVEL", "info").lower()

    print(f"Starting Agent Orchestrator API Server...")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Reload: {reload}")
    print(f"  Log Level: {log_level}")
    print(f"\nAPI will be available at: http://{host if host != '0.0.0.0' else 'localhost'}:{port}")
    print(f"Interactive docs at: http://{host if host != '0.0.0.0' else 'localhost'}:{port}/docs\n")

    uvicorn.run(
        "agent_orchestrator.api.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )
