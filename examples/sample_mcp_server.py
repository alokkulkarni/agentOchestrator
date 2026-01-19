"""
Sample MCP server using FastMCP 2.0.

This module demonstrates how to create an MCP server that can be
called by the orchestrator via the MCP protocol.

Run this server separately:
    python examples/sample_mcp_server.py
"""

import asyncio
from typing import Any, Dict

from fastmcp import FastMCP

# Create MCP server instance
mcp = FastMCP("Calculator Server")


@mcp.tool()
def add(a: float, b: float) -> Dict[str, Any]:
    """
    Add two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        Result of addition
    """
    result = a + b
    return {
        "result": result,
        "operation": "add",
        "operands": [a, b],
        "expression": f"{a} + {b} = {result}",
    }


@mcp.tool()
def subtract(a: float, b: float) -> Dict[str, Any]:
    """
    Subtract two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        Result of subtraction
    """
    result = a - b
    return {
        "result": result,
        "operation": "subtract",
        "operands": [a, b],
        "expression": f"{a} - {b} = {result}",
    }


@mcp.tool()
def multiply(a: float, b: float) -> Dict[str, Any]:
    """
    Multiply two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        Result of multiplication
    """
    result = a * b
    return {
        "result": result,
        "operation": "multiply",
        "operands": [a, b],
        "expression": f"{a} * {b} = {result}",
    }


@mcp.tool()
def divide(a: float, b: float) -> Dict[str, Any]:
    """
    Divide two numbers.

    Args:
        a: First number (numerator)
        b: Second number (denominator)

    Returns:
        Result of division

    Raises:
        ValueError: If dividing by zero
    """
    if b == 0:
        raise ValueError("Division by zero")

    result = a / b
    return {
        "result": result,
        "operation": "divide",
        "operands": [a, b],
        "expression": f"{a} / {b} = {result}",
    }


@mcp.tool()
async def get_weather(city: str) -> Dict[str, Any]:
    """
    Get weather information for a city (mock data).

    This is an async tool demonstrating async MCP support.

    Args:
        city: Name of the city

    Returns:
        Weather information
    """
    # Simulate API call delay
    await asyncio.sleep(0.2)

    # Mock weather data
    mock_weather = {
        "new york": {"temp": 72, "condition": "Sunny", "humidity": 65},
        "london": {"temp": 60, "condition": "Cloudy", "humidity": 75},
        "tokyo": {"temp": 68, "condition": "Rainy", "humidity": 80},
        "paris": {"temp": 65, "condition": "Partly Cloudy", "humidity": 70},
    }

    city_lower = city.lower()
    if city_lower in mock_weather:
        data = mock_weather[city_lower]
        return {
            "city": city,
            "temperature": data["temp"],
            "condition": data["condition"],
            "humidity": data["humidity"],
            "unit": "fahrenheit",
        }
    else:
        return {
            "city": city,
            "temperature": 70,
            "condition": "Unknown",
            "humidity": 50,
            "unit": "fahrenheit",
            "note": "Mock data for unknown city",
        }


# Add server health check endpoint
@mcp.resource("server://health")
def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.

    Returns:
        Server health status
    """
    return {
        "status": "healthy",
        "server": "Calculator Server",
        "tools": ["add", "subtract", "multiply", "divide", "get_weather"],
    }


if __name__ == "__main__":
    # Run the MCP server
    # By default, FastMCP runs on HTTP
    print("Starting Calculator MCP Server...")
    print("Available tools: add, subtract, multiply, divide, get_weather")
    print("Server will be available at http://localhost:8080")
    print("\nTo run via HTTP:")
    print("  python examples/sample_mcp_server.py --http")
    print("\nTo run via stdio:")
    print("  python examples/sample_mcp_server.py")

    import sys

    # Check if --http flag is provided
    if "--http" in sys.argv:
        print("\n✅ Starting HTTP server on http://localhost:8080")
        # Run the server with HTTP transport
        mcp.run(transport="sse", port=8080)
    else:
        print("\n✅ Starting stdio server (for direct process communication)")
        # Run the server with stdio transport (for subprocess-based MCP)
        mcp.run(transport="stdio")
