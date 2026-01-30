
"""
FastAPI server for MCP Server Gateway.
"""

import logging
import os
import time
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from ..server_gateway import ServerGateway
from .models import QueryRequest, QueryResponse

logger = logging.getLogger(__name__)

gateway: Optional[ServerGateway] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global gateway
    
    # Config
    # Default to mcp_server_gateway/config/mcp_servers.yaml relative to CWD
    root_dir = os.getcwd()
    config_path = os.path.join(root_dir, "mcp_server_gateway/config/mcp_servers.yaml")
    
    # AI Config
    gateway_url = os.getenv("MODEL_GATEWAY_URL")
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not gateway_url and not api_key:
        logger.warning("Neither MODEL_GATEWAY_URL nor ANTHROPIC_API_KEY set. Gateway initialization may fail.")

    logger.info(f"Starting MCP Gateway with config: {config_path}")
    if gateway_url:
        logger.info(f"Using Model Gateway: {gateway_url}")
    
    gateway = ServerGateway(config_path, gateway_url=gateway_url, api_key=api_key)
    try:
        await gateway.initialize()
        logger.info("Gateway initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Gateway: {e}")
    
    yield
    
    await gateway.shutdown()

app = FastAPI(
    title="MCP Server Gateway API",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/v1/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    if not gateway:
         raise HTTPException(503, "Gateway not initialized")
         
    request_id = str(uuid.uuid4())
    
    try:
        # Process
        # Combine explicit fields into metadata or context if needed
        context = request.metadata or {}
        if request.operation: context['operation'] = request.operation
        if request.operands: context['operands'] = request.operands
        
        result = await gateway.process_request(request.query, context)
        
        # Safe access to result keys
        success = result.get("success", False)
        error_msg = result.get("error")
        plan_dict = result.get("plan")
        
        return QueryResponse(
            success=success,
            data=result.get("results", {}),
            formatted_text=result.get("response"),
            request_id=request_id,
            session_id=request.session_id,
            metadata=plan_dict,
            errors=[{"message": error_msg}] if error_msg else None
        )
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return QueryResponse(
            success=False,
            data={},
            formatted_text="Internal Server Error",
            request_id=request_id,
            errors=[{"message": str(e)}]
        )

@app.get("/health")
async def health():
    return {"status": "healthy", "gateway_initialized": gateway._initialized if gateway else False}
