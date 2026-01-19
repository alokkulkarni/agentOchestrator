"""
Streaming support for orchestrator API.

Implements Server-Sent Events (SSE) for real-time query progress updates.
"""

import asyncio
import json
import time
from typing import AsyncGenerator, Dict, Any, Optional
from datetime import datetime


class StreamingCallback:
    """Callback handler for streaming orchestrator events."""

    def __init__(self):
        self.queue = asyncio.Queue()
        self._closed = False

    async def emit(self, event: str, data: Dict[str, Any]):
        """Emit an event to the stream."""
        if not self._closed:
            await self.queue.put({
                "event": event,
                "data": data,
                "timestamp": time.time()
            })

    async def close(self):
        """Close the stream."""
        self._closed = True
        await self.queue.put(None)  # Sentinel value

    async def get_events(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Get events from the queue."""
        while True:
            event = await self.queue.get()
            if event is None:  # Sentinel value
                break
            yield event


def format_sse(event: str, data: Dict[str, Any], event_id: Optional[str] = None) -> str:
    """
    Format data as Server-Sent Event.

    Args:
        event: Event name
        data: Event data (will be JSON serialized)
        event_id: Optional event ID

    Returns:
        Formatted SSE string
    """
    lines = []

    if event_id:
        lines.append(f"id: {event_id}")

    lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data)}")
    lines.append("")  # Empty line to mark end of event

    return "\n".join(lines) + "\n"


async def stream_query_progress(
    orchestrator,
    request_data: Dict[str, Any],
    request_id: str,
    session_id: Optional[str] = None,
    validate_input: bool = True,
) -> AsyncGenerator[str, None]:
    """
    Stream query processing progress as Server-Sent Events.

    Args:
        orchestrator: Orchestrator instance
        request_data: Request data to process
        request_id: Request correlation ID
        session_id: Optional session ID
        validate_input: Whether to validate input

    Yields:
        SSE formatted strings
    """
    callback = StreamingCallback()
    start_time = time.time()

    try:
        # Emit started event
        yield format_sse("started", {
            "request_id": request_id,
            "session_id": session_id,
            "query": request_data.get("query", ""),
            "message": "Query processing started"
        }, event_id=request_id)

        # Create a task to process the query
        async def process_with_callbacks():
            try:
                # Emit security validation event
                await callback.emit("security_validation", {
                    "message": "Validating input security",
                    "enabled": validate_input
                })

                # Emit reasoning event
                await callback.emit("reasoning_started", {
                    "message": "Determining agent selection",
                    "reasoning_mode": orchestrator.config.reasoning_mode
                })

                # Process the query
                result = await orchestrator.process(
                    request_data,
                    validate_input_security=validate_input,
                    request_id=request_id,
                    session_id=session_id,
                )

                # Emit reasoning complete
                metadata = result.get("_metadata", {})
                reasoning = metadata.get("reasoning", {})

                if reasoning:
                    await callback.emit("reasoning_complete", {
                        "agents_selected": reasoning.get("agents", []),
                        "method": reasoning.get("method", ""),
                        "confidence": reasoning.get("confidence", 0),
                        "parallel": reasoning.get("parallel", False)
                    })

                # Emit agent execution
                agent_trail = metadata.get("agent_trail", [])
                if agent_trail:
                    await callback.emit("agents_executing", {
                        "agents": agent_trail,
                        "message": f"Executing {len(agent_trail)} agent(s)"
                    })

                # Emit validation (if present)
                validation = metadata.get("validation", {})
                if validation:
                    await callback.emit("validation", {
                        "is_valid": validation.get("is_valid", True),
                        "confidence": validation.get("confidence_score", 0),
                        "hallucination_detected": validation.get("hallucination_detected", False)
                    })

                # Emit completion
                duration = time.time() - start_time
                await callback.emit("completed", {
                    "success": result.get("success", False),
                    "duration_seconds": round(duration, 3),
                    "result": result
                })

            except Exception as e:
                # Emit error
                await callback.emit("error", {
                    "message": str(e),
                    "error_type": type(e).__name__
                })

            finally:
                await callback.close()

        # Start processing in background
        process_task = asyncio.create_task(process_with_callbacks())

        # Stream events as they come
        async for event in callback.get_events():
            yield format_sse(
                event["event"],
                event["data"],
                event_id=request_id
            )

        # Wait for processing to complete
        await process_task

    except asyncio.CancelledError:
        # Client disconnected
        yield format_sse("cancelled", {
            "message": "Stream cancelled by client"
        }, event_id=request_id)

    except Exception as e:
        # Unexpected error
        yield format_sse("error", {
            "message": str(e),
            "error_type": type(e).__name__
        }, event_id=request_id)
