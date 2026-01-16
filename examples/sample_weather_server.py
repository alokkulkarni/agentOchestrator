"""
Sample Weather MCP server using FastMCP 2.0.

This module demonstrates a dedicated weather service MCP server that can be
called by the orchestrator via the MCP protocol.

Run this server separately:
    python examples/sample_weather_server.py
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

# Create MCP server instance
mcp = FastMCP("Weather Service")


# Mock weather database
WEATHER_DATA = {
    "new york": {
        "temp": 72,
        "temp_min": 65,
        "temp_max": 78,
        "condition": "Sunny",
        "humidity": 65,
        "wind_speed": 8,
        "pressure": 1013,
    },
    "london": {
        "temp": 60,
        "temp_min": 55,
        "temp_max": 63,
        "condition": "Cloudy",
        "humidity": 75,
        "wind_speed": 12,
        "pressure": 1010,
    },
    "tokyo": {
        "temp": 68,
        "temp_min": 62,
        "temp_max": 75,
        "condition": "Rainy",
        "humidity": 80,
        "wind_speed": 6,
        "pressure": 1008,
    },
    "paris": {
        "temp": 65,
        "temp_min": 58,
        "temp_max": 70,
        "condition": "Partly Cloudy",
        "humidity": 70,
        "wind_speed": 10,
        "pressure": 1012,
    },
    "san francisco": {
        "temp": 68,
        "temp_min": 62,
        "temp_max": 73,
        "condition": "Foggy",
        "humidity": 78,
        "wind_speed": 14,
        "pressure": 1015,
    },
    "sydney": {
        "temp": 75,
        "temp_min": 68,
        "temp_max": 82,
        "condition": "Sunny",
        "humidity": 60,
        "wind_speed": 9,
        "pressure": 1016,
    },
}


@mcp.tool()
async def get_weather(city: str, units: str = "fahrenheit") -> Dict[str, Any]:
    """
    Get current weather information for a city.

    This is a mock weather service demonstrating async MCP tool support.

    Args:
        city: Name of the city (e.g., "New York", "London")
        units: Temperature units - "fahrenheit" or "celsius" (default: fahrenheit)

    Returns:
        Weather information including temperature, condition, humidity, etc.
    """
    # Simulate API call delay
    await asyncio.sleep(0.3)

    city_lower = city.lower()

    if city_lower in WEATHER_DATA:
        data = WEATHER_DATA[city_lower].copy()

        # Convert temperature if needed
        if units.lower() == "celsius":
            data["temp"] = round((data["temp"] - 32) * 5/9, 1)
            data["temp_min"] = round((data["temp_min"] - 32) * 5/9, 1)
            data["temp_max"] = round((data["temp_max"] - 32) * 5/9, 1)

        return {
            "city": city,
            "temperature": data["temp"],
            "temp_min": data["temp_min"],
            "temp_max": data["temp_max"],
            "condition": data["condition"],
            "humidity": data["humidity"],
            "wind_speed": data["wind_speed"],
            "pressure": data["pressure"],
            "units": units,
            "timestamp": datetime.utcnow().isoformat(),
        }
    else:
        # Return default data for unknown cities
        return {
            "city": city,
            "temperature": 70 if units == "fahrenheit" else 21,
            "temp_min": 65 if units == "fahrenheit" else 18,
            "temp_max": 75 if units == "fahrenheit" else 24,
            "condition": "Unknown",
            "humidity": 50,
            "wind_speed": 5,
            "pressure": 1013,
            "units": units,
            "timestamp": datetime.utcnow().isoformat(),
            "note": "Mock data for unknown city",
        }


@mcp.tool()
async def get_forecast(city: str, days: int = 5, units: str = "fahrenheit") -> Dict[str, Any]:
    """
    Get weather forecast for a city.

    Args:
        city: Name of the city
        days: Number of days to forecast (1-7, default: 5)
        units: Temperature units - "fahrenheit" or "celsius"

    Returns:
        Weather forecast for the specified number of days
    """
    # Validate days
    days = max(1, min(days, 7))

    # Simulate API call delay
    await asyncio.sleep(0.4)

    city_lower = city.lower()

    # Get base weather data
    if city_lower in WEATHER_DATA:
        base_data = WEATHER_DATA[city_lower]
    else:
        base_data = {
            "temp": 70,
            "temp_min": 65,
            "temp_max": 75,
            "condition": "Unknown",
            "humidity": 50,
            "wind_speed": 5,
            "pressure": 1013,
        }

    # Generate forecast
    forecast = []
    conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Rainy", "Clear"]

    for i in range(days):
        date = datetime.utcnow() + timedelta(days=i)

        # Slight variation in temperature
        temp_variation = (i % 3 - 1) * 3
        temp = base_data["temp"] + temp_variation
        temp_min = base_data["temp_min"] + temp_variation
        temp_max = base_data["temp_max"] + temp_variation

        # Convert if needed
        if units.lower() == "celsius":
            temp = round((temp - 32) * 5/9, 1)
            temp_min = round((temp_min - 32) * 5/9, 1)
            temp_max = round((temp_max - 32) * 5/9, 1)

        forecast.append({
            "date": date.strftime("%Y-%m-%d"),
            "day_of_week": date.strftime("%A"),
            "temperature": temp,
            "temp_min": temp_min,
            "temp_max": temp_max,
            "condition": conditions[i % len(conditions)],
            "humidity": base_data["humidity"] + (i % 2) * 5,
            "wind_speed": base_data["wind_speed"] + (i % 3),
            "pressure": base_data["pressure"] + (i % 2 - 1) * 2,
        })

    return {
        "city": city,
        "forecast": forecast,
        "units": units,
        "days": days,
        "generated_at": datetime.utcnow().isoformat(),
    }


@mcp.tool()
async def get_air_quality(city: str) -> Dict[str, Any]:
    """
    Get air quality index (AQI) for a city.

    Args:
        city: Name of the city

    Returns:
        Air quality information including AQI score and pollutant levels
    """
    # Simulate API call delay
    await asyncio.sleep(0.2)

    # Mock AQI data
    mock_aqi = {
        "new york": {"aqi": 45, "category": "Good", "pm25": 12, "pm10": 20},
        "london": {"aqi": 62, "category": "Moderate", "pm25": 18, "pm10": 30},
        "tokyo": {"aqi": 38, "category": "Good", "pm25": 10, "pm10": 18},
        "paris": {"aqi": 55, "category": "Moderate", "pm25": 15, "pm10": 25},
        "san francisco": {"aqi": 42, "category": "Good", "pm25": 11, "pm10": 19},
        "sydney": {"aqi": 35, "category": "Good", "pm25": 9, "pm10": 16},
    }

    city_lower = city.lower()

    if city_lower in mock_aqi:
        data = mock_aqi[city_lower]
    else:
        data = {"aqi": 50, "category": "Moderate", "pm25": 15, "pm10": 25}

    return {
        "city": city,
        "aqi": data["aqi"],
        "category": data["category"],
        "pollutants": {
            "pm2.5": data["pm25"],
            "pm10": data["pm10"],
        },
        "health_advice": _get_health_advice(data["aqi"]),
        "timestamp": datetime.utcnow().isoformat(),
    }


@mcp.tool()
async def get_alerts(city: str) -> Dict[str, Any]:
    """
    Get weather alerts and warnings for a city.

    Args:
        city: Name of the city

    Returns:
        List of active weather alerts
    """
    # Simulate API call delay
    await asyncio.sleep(0.2)

    # Mock alerts (most cities have none)
    alerts = []

    city_lower = city.lower()
    if city_lower == "tokyo":
        alerts.append({
            "type": "Heavy Rain Warning",
            "severity": "Moderate",
            "description": "Heavy rainfall expected in the next 24 hours",
            "issued_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        })
    elif city_lower == "san francisco":
        alerts.append({
            "type": "Dense Fog Advisory",
            "severity": "Minor",
            "description": "Dense fog may reduce visibility",
            "issued_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=6)).isoformat(),
        })

    return {
        "city": city,
        "alerts": alerts,
        "count": len(alerts),
        "timestamp": datetime.utcnow().isoformat(),
    }


@mcp.tool()
def list_cities() -> Dict[str, Any]:
    """
    List all cities available in the mock weather database.

    Returns:
        List of available cities
    """
    return {
        "cities": sorted(WEATHER_DATA.keys()),
        "count": len(WEATHER_DATA),
        "note": "These cities have detailed mock weather data. Other cities return default values.",
    }


# Helper functions
def _get_health_advice(aqi: int) -> str:
    """Get health advice based on AQI value."""
    if aqi <= 50:
        return "Air quality is good. Enjoy outdoor activities."
    elif aqi <= 100:
        return "Air quality is moderate. Sensitive individuals should limit prolonged outdoor exertion."
    elif aqi <= 150:
        return "Air quality is unhealthy for sensitive groups. Reduce prolonged outdoor exertion."
    elif aqi <= 200:
        return "Air quality is unhealthy. Avoid prolonged outdoor exertion."
    elif aqi <= 300:
        return "Air quality is very unhealthy. Avoid all outdoor exertion."
    else:
        return "Air quality is hazardous. Stay indoors."


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
        "server": "Weather Service",
        "version": "1.0.0",
        "tools": [
            "get_weather",
            "get_forecast",
            "get_air_quality",
            "get_alerts",
            "list_cities",
        ],
        "cities_available": len(WEATHER_DATA),
    }


if __name__ == "__main__":
    # Run the MCP server
    print("=" * 60)
    print("Starting Weather Service MCP Server...")
    print("=" * 60)
    print("\nAvailable tools:")
    print("  - get_weather(city, units): Get current weather")
    print("  - get_forecast(city, days, units): Get weather forecast")
    print("  - get_air_quality(city): Get air quality index")
    print("  - get_alerts(city): Get weather alerts")
    print("  - list_cities(): List available cities")
    print("\nAvailable cities:")
    print("  " + ", ".join(sorted(WEATHER_DATA.keys())))
    print("\nServer will be available via stdio transport")
    print("=" * 60)

    # Run the server (FastMCP will handle stdio transport)
    mcp.run(transport="stdio")
