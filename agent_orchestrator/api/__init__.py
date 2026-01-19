"""
FastAPI server for Agent Orchestrator.

Provides REST API endpoints for querying the orchestrator with streaming support.
"""

from .server import app

__all__ = ["app"]
