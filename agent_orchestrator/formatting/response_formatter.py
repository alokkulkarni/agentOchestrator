"""
Response formatter for creating user-friendly output from agent responses.

Converts raw agent data into human-readable text that can be displayed directly to users.
"""

from typing import Any, Dict, List


class ResponseFormatter:
    """Formats agent responses into human-readable text."""

    def format_response(self, data: Dict[str, Any]) -> str:
        """
        Format agent responses into user-friendly text.

        Args:
            data: Dictionary of agent responses (agent_name -> agent_data)

        Returns:
            Formatted text suitable for direct display to users
        """
        if not data:
            return "No results available."

        formatted_parts = []

        for agent_name, agent_data in data.items():
            formatted = self._format_agent_response(agent_name, agent_data)
            if formatted:
                formatted_parts.append(formatted)

        return "\n\n".join(formatted_parts) if formatted_parts else "No results available."

    def _format_agent_response(self, agent_name: str, agent_data: Any) -> str:
        """Format a single agent's response."""
        if not isinstance(agent_data, dict):
            return f"{agent_name}: {agent_data}"

        # Weather agent
        if 'location' in agent_data and 'current' in agent_data:
            return self._format_weather(agent_data)

        # Calculator agent
        elif 'result' in agent_data and 'operation' in agent_data:
            return self._format_calculator(agent_data)

        # Search agents (Tavily, local search)
        elif 'results' in agent_data and isinstance(agent_data.get('results'), list):
            return self._format_search(agent_data)

        # Data processor
        elif 'processed_data' in agent_data or 'aggregation' in agent_data:
            return self._format_data_processor(agent_data)

        # Generic fallback
        else:
            return self._format_generic(agent_name, agent_data)

    def _format_weather(self, data: Dict[str, Any]) -> str:
        """Format weather data into readable text."""
        lines = []

        # Location
        location = data.get('location', {})
        loc_name = location.get('name', 'Unknown')
        country = location.get('country', '')

        if country and country != 'Unknown':
            lines.append(f"📍 Weather for {loc_name}, {country}")
        else:
            lines.append(f"📍 Weather for {loc_name}")

        lines.append("")

        # Current conditions
        current = data.get('current', {})
        unit_symbol = data.get('unit_symbol', '°C')

        temp = current.get('temp')
        description = current.get('description', 'N/A')

        if temp is not None:
            lines.append(f"🌡️  Temperature: {temp}{unit_symbol}")

        feels_like = current.get('feels_like')
        if feels_like is not None:
            lines.append(f"💨 Feels like: {feels_like}{unit_symbol}")

        if description:
            lines.append(f"☁️  Conditions: {description.title()}")

        # Additional details
        humidity = current.get('humidity')
        if humidity is not None:
            lines.append(f"💧 Humidity: {humidity}%")

        wind_speed = current.get('wind_speed')
        if wind_speed is not None:
            lines.append(f"🌬️  Wind: {wind_speed} m/s")

        temp_min = current.get('temp_min')
        temp_max = current.get('temp_max')
        if temp_min is not None and temp_max is not None:
            lines.append(f"📊 Range: {temp_min}{unit_symbol} - {temp_max}{unit_symbol}")

        # Visibility
        visibility = current.get('visibility')
        if visibility is not None and visibility > 0:
            visibility_km = visibility / 1000
            lines.append(f"👁️  Visibility: {visibility_km:.1f} km")

        # Note
        if 'note' in data:
            lines.append("")
            lines.append(f"ℹ️  {data['note']}")

        return "\n".join(lines)

    def _format_calculator(self, data: Dict[str, Any]) -> str:
        """Format calculator results into readable text."""
        result = data.get('result')
        operation = data.get('operation', 'calculation')
        expression = data.get('expression', '')

        if expression:
            return f"🔢 {expression} = {result}"
        else:
            return f"🔢 Result: {result} ({operation})"

    def _format_search(self, data: Dict[str, Any]) -> str:
        """Format search results into readable text."""
        lines = []

        # AI-generated answer
        if 'answer' in data and data['answer']:
            lines.append("💡 Answer:")
            lines.append(data['answer'])
            lines.append("")

        # Results summary
        results = data.get('results', [])
        total = data.get('total_results', data.get('total_count', len(results)))

        if not results:
            lines.append(f"🔍 No results found")
            return "\n".join(lines)

        lines.append(f"🔍 Found {total} result(s):")
        lines.append("")

        # Top results
        for i, result in enumerate(results[:5], 1):
            title = result.get('title', 'Untitled')
            url = result.get('url', '')
            content = result.get('content', result.get('snippet', ''))

            lines.append(f"{i}. {title}")

            if content:
                # Truncate long content
                if len(content) > 150:
                    content = content[:150] + "..."
                lines.append(f"   {content}")

            if url:
                lines.append(f"   🔗 {url}")

            lines.append("")

        return "\n".join(lines)

    def _format_data_processor(self, data: Dict[str, Any]) -> str:
        """Format data processor results into readable text."""
        lines = []

        # Aggregation results
        if 'aggregation' in data:
            agg = data['aggregation']
            lines.append("📊 Data Summary:")
            for key, value in agg.items():
                if isinstance(value, float):
                    lines.append(f"  • {key}: {value:.2f}")
                else:
                    lines.append(f"  • {key}: {value}")

        # Processed data
        elif 'processed_data' in data:
            processed = data['processed_data']
            if isinstance(processed, list):
                lines.append(f"📋 Processed {len(processed)} record(s)")
                # Show first few records
                for i, record in enumerate(processed[:3], 1):
                    if isinstance(record, dict):
                        record_str = ", ".join(f"{k}: {v}" for k, v in list(record.items())[:3])
                        lines.append(f"  {i}. {record_str}")
            else:
                lines.append(f"📋 Result: {processed}")

        # Operation info
        if 'operation' in data:
            lines.append(f"\n✓ Operation: {data['operation']}")

        return "\n".join(lines) if lines else self._format_generic("data_processor", data)

    def _format_generic(self, agent_name: str, data: Dict[str, Any]) -> str:
        """Generic formatter for unknown agent types."""
        lines = [f"📤 {agent_name.replace('_', ' ').title()} Results:"]

        # Try to extract key information
        if 'success' in data and not data['success']:
            error = data.get('error', 'Unknown error')
            lines.append(f"❌ Error: {error}")
            return "\n".join(lines)

        # Show important fields
        important_fields = ['message', 'result', 'output', 'response', 'data', 'summary']

        found_content = False
        for field in important_fields:
            if field in data:
                value = data[field]
                if isinstance(value, (str, int, float, bool)):
                    lines.append(f"{value}")
                    found_content = True
                    break
                elif isinstance(value, list) and len(value) <= 5:
                    for item in value:
                        lines.append(f"  • {item}")
                    found_content = True
                    break

        if not found_content:
            # Fallback: show first few non-meta fields
            skip_fields = {'success', 'timestamp', 'metadata', 'request_id'}
            for key, value in data.items():
                if key in skip_fields:
                    continue
                if isinstance(value, (str, int, float, bool)):
                    lines.append(f"{key}: {value}")
                elif isinstance(value, list) and len(value) <= 3:
                    lines.append(f"{key}: {', '.join(str(v) for v in value)}")

        return "\n".join(lines)
