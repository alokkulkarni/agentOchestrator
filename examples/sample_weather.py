"""
Simple Weather Agent using OpenWeatherMap API

Provides current weather and forecasts for locations worldwide.
Free tier: 1000 calls/day, no credit card required.

API: https://openweathermap.org/api
"""

import asyncio
import os
from datetime import datetime
from typing import Any, Dict, Optional

try:
    import aiohttp
except ImportError:
    aiohttp = None


def get_weather(
    query: Optional[str] = None,
    location: Optional[str] = None,
    units: str = "metric",
    include_forecast: bool = False,
) -> Dict[str, Any]:
    """
    Get weather information (synchronous wrapper).

    Args:
        query: Natural language query (e.g., "weather in Glasgow")
        location: City name (e.g., "Glasgow, Scotland" or "London, UK")
                 If not provided, will be extracted from query
        units: "metric" (Celsius), "imperial" (Fahrenheit), or "standard" (Kelvin)
        include_forecast: Include 5-day forecast

    Returns:
        Dictionary with weather data
    """
    # Extract location from query if not provided
    if not location and query:
        location = _extract_location_from_query(query)

    if not location:
        return {
            "success": False,
            "error": "No location provided. Please specify a city or location.",
        }

    return asyncio.run(
        weather_search(
            location=location,
            units=units,
            include_forecast=include_forecast,
        )
    )


def _extract_location_from_query(query: str) -> str:
    """
    Extract location from natural language query.

    Examples:
        "weather in Glasgow" -> "Glasgow"
        "what's the temperature in London, UK" -> "London, UK"
        "Glasgow Scotland weather tomorrow" -> "Glasgow, Scotland"
    """
    import re

    query_lower = query.lower()

    # Common patterns
    patterns = [
        r'(?:weather|temperature|forecast|climate)\s+(?:in|for|at)\s+([^?.,]+)',
        r'(?:in|at)\s+([a-zA-Z\s,]+)(?:\s+tomorrow|\s+today|\s+weather|$)',
        r'^([a-zA-Z\s,]+?)(?:\s+weather|\s+tomorrow|\s+forecast)',
    ]

    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            location = match.group(1).strip()
            # Clean up common trailing words
            location = re.sub(r'\s+(weather|tomorrow|today|forecast|temperature)$', '', location, flags=re.IGNORECASE)
            if location:
                return location

    # Fallback: return the query as-is (let the API try to interpret it)
    return query


async def weather_search(
    location: str,
    units: str = "metric",
    include_forecast: bool = False,
) -> Dict[str, Any]:
    """
    Get weather information using OpenWeatherMap API.

    Args:
        location: City name, state, country (e.g., "Glasgow, Scotland")
        units: Temperature units - "metric" (°C), "imperial" (°F), or "standard" (K)
        include_forecast: Include 5-day weather forecast

    Returns:
        Dictionary containing:
        - success: bool - Whether the request succeeded
        - location: str - Location name
        - current: Dict - Current weather data
        - forecast: List[Dict] - Forecast data (if requested)
        - timestamp: str - When the data was retrieved

    Example:
        >>> result = await weather_search("Glasgow, Scotland")
        >>> print(f"{result['current']['temp']}°C, {result['current']['description']}")
    """
    # Check if aiohttp is installed
    if aiohttp is None:
        return {
            "success": False,
            "error": "aiohttp not installed. Install with: pip install aiohttp",
            "location": location,
        }

    # Get API key from environment
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        # Return mock data if no API key is set
        return _get_mock_weather(location, units, include_forecast)

    try:
        # Validate units
        if units not in ["metric", "imperial", "standard"]:
            units = "metric"

        async with aiohttp.ClientSession() as session:
            # Get current weather
            current_url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                "q": location,
                "appid": api_key,
                "units": units,
            }

            async with session.get(current_url, params=params) as response:
                if response.status != 200:
                    error_data = await response.json()
                    return {
                        "success": False,
                        "error": error_data.get("message", "API request failed"),
                        "location": location,
                        "status_code": response.status,
                    }

                data = await response.json()

                # Parse current weather
                current_weather = {
                    "temp": data["main"]["temp"],
                    "feels_like": data["main"]["feels_like"],
                    "temp_min": data["main"]["temp_min"],
                    "temp_max": data["main"]["temp_max"],
                    "humidity": data["main"]["humidity"],
                    "pressure": data["main"]["pressure"],
                    "description": data["weather"][0]["description"],
                    "main": data["weather"][0]["main"],
                    "icon": data["weather"][0]["icon"],
                    "wind_speed": data["wind"]["speed"],
                    "wind_deg": data["wind"].get("deg", 0),
                    "clouds": data["clouds"]["all"],
                    "visibility": data.get("visibility", 0),
                }

                # Add rain/snow if present
                if "rain" in data:
                    current_weather["rain"] = data["rain"]
                if "snow" in data:
                    current_weather["snow"] = data["snow"]

                result = {
                    "success": True,
                    "location": {
                        "name": data["name"],
                        "country": data["sys"]["country"],
                        "coord": data["coord"],
                        "timezone": data["timezone"],
                    },
                    "current": current_weather,
                    "units": units,
                    "unit_symbol": "°C" if units == "metric" else ("°F" if units == "imperial" else "K"),
                    "timestamp": datetime.utcnow().isoformat(),
                }

                # Get forecast if requested
                if include_forecast:
                    forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
                    async with session.get(forecast_url, params=params) as forecast_response:
                        if forecast_response.status == 200:
                            forecast_data = await forecast_response.json()
                            result["forecast"] = _parse_forecast(forecast_data, units)

                return result

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "location": location,
            "timestamp": datetime.utcnow().isoformat(),
        }


def _parse_forecast(data: Dict, units: str) -> list:
    """Parse 5-day forecast data."""
    forecast = []
    for item in data["list"][:8]:  # Next 24 hours (8 * 3-hour periods)
        forecast.append({
            "time": item["dt_txt"],
            "temp": item["main"]["temp"],
            "feels_like": item["main"]["feels_like"],
            "description": item["weather"][0]["description"],
            "main": item["weather"][0]["main"],
            "humidity": item["main"]["humidity"],
            "wind_speed": item["wind"]["speed"],
            "clouds": item["clouds"]["all"],
            "pop": item.get("pop", 0) * 100,  # Probability of precipitation
        })
    return forecast


def _get_mock_weather(location: str, units: str, include_forecast: bool) -> Dict[str, Any]:
    """
    Return mock weather data when API key is not available.
    Useful for testing without an API key.
    """
    unit_symbol = "°C" if units == "metric" else ("°F" if units == "imperial" else "K")
    temp = 12 if units == "metric" else 54 if units == "imperial" else 285

    result = {
        "success": True,
        "location": {
            "name": location.split(",")[0].strip(),
            "country": "Unknown",
            "coord": {"lat": 0, "lon": 0},
            "timezone": 0,
        },
        "current": {
            "temp": temp,
            "feels_like": temp - 2,
            "temp_min": temp - 3,
            "temp_max": temp + 2,
            "humidity": 75,
            "pressure": 1013,
            "description": "partly cloudy",
            "main": "Clouds",
            "icon": "02d",
            "wind_speed": 5.2,
            "wind_deg": 180,
            "clouds": 40,
            "visibility": 10000,
        },
        "units": units,
        "unit_symbol": unit_symbol,
        "timestamp": datetime.utcnow().isoformat(),
        "note": "Using mock data - set OPENWEATHER_API_KEY for real data",
    }

    if include_forecast:
        result["forecast"] = [
            {
                "time": f"2026-01-20 {3*i:02d}:00:00",
                "temp": temp + i - 2,
                "feels_like": temp + i - 4,
                "description": "partly cloudy",
                "main": "Clouds",
                "humidity": 70 + i,
                "wind_speed": 5.0 + i * 0.5,
                "clouds": 40 + i * 5,
                "pop": 10 + i * 5,
            }
            for i in range(8)
        ]

    return result


# Test function
async def test_weather():
    """Test the weather agent."""
    print("=" * 70)
    print("WEATHER AGENT TEST")
    print("=" * 70)

    # Test 1: Glasgow weather
    print("\n" + "-" * 70)
    print("Test 1: Glasgow, Scotland Weather")
    print("-" * 70)

    result = await weather_search("Glasgow, Scotland", units="metric")

    print(f"\nSuccess: {result['success']}")
    if result['success']:
        loc = result['location']
        cur = result['current']
        print(f"\n📍 Location: {loc['name']}, {loc['country']}")
        print(f"🌡️  Temperature: {cur['temp']}{result['unit_symbol']}")
        print(f"   Feels like: {cur['feels_like']}{result['unit_symbol']}")
        print(f"   Min/Max: {cur['temp_min']}/{cur['temp_max']}{result['unit_symbol']}")
        print(f"☁️  Conditions: {cur['description'].title()}")
        print(f"💧 Humidity: {cur['humidity']}%")
        print(f"🌬️  Wind: {cur['wind_speed']} m/s")

        if 'note' in result:
            print(f"\n⚠️  {result['note']}")
    else:
        print(f"Error: {result.get('error')}")

    # Test 2: With forecast
    print("\n" + "-" * 70)
    print("Test 2: London Weather with Forecast")
    print("-" * 70)

    result = await weather_search("London, UK", units="metric", include_forecast=True)

    print(f"\nSuccess: {result['success']}")
    if result['success']:
        print(f"📍 Location: {result['location']['name']}")
        print(f"🌡️  Current: {result['current']['temp']}{result['unit_symbol']}, {result['current']['description']}")

        if 'forecast' in result:
            print(f"\n📅 Next 24 hours:")
            for f in result['forecast'][:4]:
                print(f"   {f['time']}: {f['temp']}{result['unit_symbol']}, {f['description']}")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_weather())
