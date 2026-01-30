"""
Response formatter for creating user-friendly output from agent responses.

Converts raw agent data into human-readable text that can be displayed directly to users.
"""

from typing import Any, Dict, List


class ResponseFormatter:
    """Formats agent responses into human-readable text."""

    def __init__(self):
        """Initialize the response formatter."""
        self.trip_keywords = ["trip", "travel", "route", "itinerary", "journey", "drive from", "points of interest"]
        self.process_keywords = ["steps", "process", "how to", "guide", "procedure", "what do i need"]

    def format_response(self, data: Dict[str, Any], original_query: str = "") -> str:
        """
        Format agent responses into user-friendly text.

        Args:
            data: Dictionary of agent responses (agent_name -> agent_data)
            original_query: The original user query (used for context-aware synthesis)

        Returns:
            Formatted text suitable for direct display to users
        """
        if not data:
            return "No results available."

        # Check if this needs orchestrator synthesis (not single-agent response)
        if self._needs_synthesis(data, original_query):
            return self._synthesize_response(data, original_query)

        formatted_parts = []

        for agent_name, agent_data in data.items():
            formatted = self._format_agent_response(agent_name, agent_data)
            if formatted:
                formatted_parts.append(formatted)

        return "\n\n".join(formatted_parts) if formatted_parts else "No results available."

    def _needs_synthesis(self, data: Dict[str, Any], query: str) -> bool:
        """
        Check if this query needs orchestrator synthesis rather than just formatting agent outputs.
        
        Synthesis is needed when:
        - Query asks for process/steps/how-to AND we have search results
        - Query is about trip planning AND we have search results
        - Multiple search agents were called (indicates complex information gathering)
        """
        if not query:
            return False
            
        # Has search results from multiple search agents or complex query
        has_search = any(agent in ['search', 'tavily_search'] for agent in data.keys())
        if not has_search:
            return False
            
        query_lower = query.lower()
        
        # Process/steps queries
        is_process_query = any(keyword in query_lower for keyword in self.process_keywords)
        
        # Trip planning queries
        is_trip_query = any(keyword in query_lower for keyword in self.trip_keywords)
        
        return is_process_query or is_trip_query

    def _synthesize_response(self, data: Dict[str, Any], query: str) -> str:
        """
        Synthesize a coherent response from search results based on query type.
        
        This is the orchestrator's internal synthesis - it combines information
        from multiple agents into a structured, coherent answer.
        """
        query_lower = query.lower()
        
        # Detect query type
        if any(keyword in query_lower for keyword in self.trip_keywords):
            return self._synthesize_trip_plan(data, query)
        elif any(keyword in query_lower for keyword in self.process_keywords):
            return self._synthesize_process_guide(data, query)
        else:
            # General information synthesis
            return self._synthesize_general_info(data, query)

    def _is_result_relevant(self, result: Dict[str, Any], query: str) -> bool:
        """
        Check if a search result is relevant to the query.
        Filters out results that are clearly unrelated (e.g., code files, programming docs).
        """
        query_lower = query.lower()
        
        # Get result content
        title = result.get('title', '').lower()
        content = result.get('content', result.get('snippet', '')).lower()
        url = result.get('url', '').lower()
        
        # Check if query is about programming/code
        is_programming_query = any(term in query_lower for term in 
            ['python', 'javascript', 'programming', 'code', 'software', 'function', 'api'])
        
        if not is_programming_query:
            # Filter out programming/code-related results
            programming_terms = [
                'python', 'javascript', 'programming', 'async', 'await',
                'function', 'class', 'import', 'asyncio', 'syntax',
                'language', 'library', 'framework'
            ]
            
            # Count programming terms in result
            prog_count = sum(1 for term in programming_terms if term in title or term in content[:300])
            
            # If result is heavily about programming, filter it out
            if prog_count >= 2:
                return False
        
        # Prefer results with proper URLs (web resources, not local files)
        if url and not url.startswith(('http://', 'https://')):
            return False
        
        # Check for keyword overlap
        query_words = set(word for word in query_lower.split() if len(word) > 3)
        result_text = (title + ' ' + content[:200]).lower()
        
        # Count matching words
        matches = sum(1 for word in query_words if word in result_text)
        
        # Need at least 2 matching words or very relevant title
        return matches >= 2 or any(word in title for word in query_words)

    def _synthesize_process_guide(self, data: Dict[str, Any], query: str) -> str:
        """
        Synthesize a process/steps guide from search results.
        
        Examples:
        - "steps to buy a house"
        - "how to start a business"
        - "process for applying for visa"
        """
        lines = []
        
        # Extract topic from query
        topic = self._extract_topic(query)
        lines.append(f"📋 Guide: {topic}")
        lines.append("")
        lines.append("=" * 80)
        lines.append("")
        
        # Collect all search results and answers with relevance filtering
        all_results = []
        answers = []
        
        for agent_name, agent_data in data.items():
            if agent_name in ['search', 'tavily_search'] and isinstance(agent_data, dict):
                if 'answer' in agent_data and agent_data['answer']:
                    answers.append(agent_data['answer'])
                if 'results' in agent_data:
                    # Filter for relevant results only
                    for result in agent_data['results']:
                        if self._is_result_relevant(result, query):
                            all_results.append(result)
        
        # AI-generated summary (if available)
        if answers:
            lines.append("📍 Overview:")
            lines.append(answers[0])  # Use first answer as main summary
            lines.append("")
        
        # Extract and structure information from results
        if all_results:
            lines.append("📖 Key Information:")
            lines.append("")
            
            # Show relevant snippets from filtered results
            for i, result in enumerate(all_results[:5], 1):
                title = result.get('title', 'Resource')
                content = result.get('content', result.get('snippet', ''))
                url = result.get('url', '')
                
                lines.append(f"{i}. {title}")
                if content:
                    if len(content) > 150:
                        content = content[:150] + "..."
                    lines.append(f"   {content}")
                if url:
                    lines.append(f"   🔗 {url}")
                lines.append("")
        
        # Add helpful tip
        lines.append("💡 Tip:")
        lines.append("   • Review official sources for the most accurate and up-to-date information")
        lines.append("   • Consider consulting with professionals for specific advice")
        lines.append("")
        
        lines.append("=" * 80)
        lines.append("")
        lines.append("ℹ️  This guide is synthesized from available information sources.")
        
        return "\n".join(lines)

    def _synthesize_general_info(self, data: Dict[str, Any], query: str) -> str:
        """
        Synthesize a general information response from search results.
        """
        lines = []
        
        # Collect all answers and filtered results
        answers = []
        all_results = []
        
        for agent_name, agent_data in data.items():
            if agent_name in ['search', 'tavily_search'] and isinstance(agent_data, dict):
                if 'answer' in agent_data and agent_data['answer']:
                    answers.append(agent_data['answer'])
                if 'results' in agent_data:
                    # Filter for relevant results
                    for result in agent_data['results']:
                        if self._is_result_relevant(result, query):
                            all_results.append(result)
        
        # Main answer
        if answers:
            lines.append("💡 Answer:")
            lines.append(answers[0])
            lines.append("")
        
        # Supporting results
        if all_results:
            lines.append(f"🔍 Found {len(all_results)} relevant result(s):")
            lines.append("")
            
            for i, result in enumerate(all_results[:5], 1):
                title = result.get('title', 'Resource')
                content = result.get('content', result.get('snippet', ''))
                url = result.get('url', '')
                
                lines.append(f"{i}. {title}")
                if content and len(content) > 100:
                    lines.append(f"   {content[:100]}...")
                if url:
                    lines.append(f"   🔗 {url}")
                lines.append("")
        
        return "\n".join(lines) if lines else "No results available."

    def _extract_topic(self, query: str) -> str:
        """Extract the main topic from the query."""
        import re
        
        # Remove common prefixes
        cleaned = re.sub(r'^(what are the |how to |steps to |process for |guide to )', '', query.lower())
        cleaned = re.sub(r'\?$', '', cleaned)  # Remove trailing question mark
        
        return cleaned.strip().title()

    def _is_trip_planning_query(self, query: str) -> bool:
        """Check if the query is about trip planning."""
        if not query:
            return False
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in self.trip_keywords)

    def _has_search_results(self, data: Dict[str, Any]) -> bool:
        """Check if data contains search results from search or tavily_search agents."""
        return any(agent_name in ['search', 'tavily_search'] for agent_name in data.keys())

    def _synthesize_trip_plan(self, data: Dict[str, Any], query: str) -> str:
        """
        Synthesize a trip plan from search results.
        
        This method extracts information from search results and creates
        a coherent trip planning response internally within the orchestrator.
        """
        lines = []
        
        # Extract origin and destination from query
        import re
        from_to_match = re.search(r'from\s+([a-zA-Z\s]+?)\s+to\s+([a-zA-Z\s]+)', query, re.IGNORECASE)
        if from_to_match:
            origin = from_to_match.group(1).strip().title()
            destination = from_to_match.group(2).strip().title()
            lines.append(f"🗺️  Trip Plan: {origin} to {destination}")
        else:
            lines.append("🗺️  Your Trip Plan")
        
        lines.append("")
        lines.append("=" * 80)
        lines.append("")
        
        # Collect all search results with relevance filtering
        all_results = []
        answer = None
        
        for agent_name, agent_data in data.items():
            if agent_name in ['search', 'tavily_search'] and isinstance(agent_data, dict):
                if 'answer' in agent_data and agent_data['answer']:
                    answer = agent_data['answer']
                if 'results' in agent_data:
                    # Filter for relevant results
                    for result in agent_data['results']:
                        if self._is_result_relevant(result, query):
                            all_results.append(result)

        
        # Summary section (from AI answer if available)
        if answer:
            lines.append("📍 Route Overview:")
            lines.append(answer)
            lines.append("")
        
        # Points of Interest section
        if all_results:
            lines.append("🎯 Points of Interest & Resources:")
            lines.append("")
            
            for i, result in enumerate(all_results[:6], 1):  # Show top 6 results
                title = result.get('title', 'Resource')
                content = result.get('content', result.get('snippet', ''))
                url = result.get('url', '')
                
                lines.append(f"{i}. {title}")
                if content:
                    # Truncate content
                    if len(content) > 120:
                        content = content[:120] + "..."
                    lines.append(f"   {content}")
                if url:
                    lines.append(f"   🔗 {url}")
                lines.append("")
        
        # Travel tips
        lines.append("💡 Travel Tips:")
        lines.append("   • Check traffic conditions before departure")
        lines.append("   • Plan for rest stops every 2-3 hours")
        lines.append("   • Consider visiting attractions during off-peak hours")
        lines.append("   • Check opening hours for points of interest")
        lines.append("")
        
        lines.append("=" * 80)
        lines.append("")
        lines.append("ℹ️  This trip plan is synthesized from available information.")
        lines.append("   For detailed navigation, please use a dedicated GPS or mapping service.")
        
        return "\n".join(lines)

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

        # Tech insights agent
        elif 'insights' in agent_data and 'total_insights' in agent_data:
            return self._format_tech_insights(agent_data)

        # Planning agent
        elif 'plan' in agent_data or 'status' in agent_data and agent_data.get('status') in ['plan_created', 'needs_clarification']:
            return self._format_planning(agent_data)

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

    def _format_tech_insights(self, data: Dict[str, Any]) -> str:
        """Format tech insights data into readable text."""
        lines = []

        # Header
        total = data.get('total_insights', 0)
        filters = data.get('filters', {})
        audience = filters.get('audience', 'both')
        category = filters.get('category')

        lines.append(f"💡 Top {total} Software Engineering Insights")
        if category:
            lines.append(f"   Category: {category.upper()}")
        lines.append(f"   Audience: {audience.title()}")
        lines.append("")
        lines.append("=" * 80)
        lines.append("")

        # Display each insight
        insights = data.get('insights', [])
        for insight in insights:
            rank = insight.get('rank', '?')
            title = insight.get('title', 'No title')
            category = insight.get('category', 'general')
            impact = insight.get('impact', 'medium')
            adoption = insight.get('adoption', 'unknown')
            source = insight.get('source', 'N/A')

            # Title with rank and metadata
            lines.append(f"{rank}. {title}")
            lines.append(f"   📂 Category: {category.upper()} | 🎯 Impact: {impact.upper()} | 📈 Adoption: {adoption.upper()}")
            lines.append(f"   📚 Source: {source}")
            lines.append("")

            # Show perspectives based on audience filter
            if audience == 'both':
                # Show both technical and non-technical
                technical = insight.get('technical', '')
                non_technical = insight.get('non_technical', '')

                if technical:
                    lines.append("   👨‍💻 TECHNICAL PERSPECTIVE:")
                    # Wrap long lines
                    for line in self._wrap_text(technical, width=75, indent=6):
                        lines.append(line)
                    lines.append("")

                if non_technical:
                    lines.append("   👥 NON-TECHNICAL PERSPECTIVE:")
                    for line in self._wrap_text(non_technical, width=75, indent=6):
                        lines.append(line)
                    lines.append("")
            else:
                # Show single perspective
                insight_text = insight.get('insight', '')
                if insight_text:
                    for line in self._wrap_text(insight_text, width=75, indent=3):
                        lines.append(line)
                    lines.append("")

            lines.append("-" * 80)
            lines.append("")

        # Footer with metadata
        metadata = data.get('metadata', {})
        if metadata:
            lines.append("")
            lines.append(f"ℹ️  Source: {metadata.get('source', 'Unknown')}")
            lines.append(f"   Version: {metadata.get('version', 'N/A')}")
            lines.append(f"   Update Frequency: {metadata.get('update_frequency', 'N/A')}")

        return "\n".join(lines)

    def _wrap_text(self, text: str, width: int = 75, indent: int = 3) -> list:
        """Wrap text to specified width with indentation."""
        words = text.split()
        lines = []
        current_line = " " * indent

        for word in words:
            if len(current_line) + len(word) + 1 <= width:
                current_line += word + " "
            else:
                lines.append(current_line.rstrip())
                current_line = " " * indent + word + " "

        if current_line.strip():
            lines.append(current_line.rstrip())

        return lines

    def _format_planning(self, data: Dict[str, Any]) -> str:
        """Format planning agent results into readable text."""
        lines = []

        status = data.get('status', 'unknown')

        # Handle clarification needed
        if status == 'needs_clarification':
            lines.append("📋 Planning Agent - Additional Information Needed")
            lines.append("")
            lines.append("=" * 80)
            lines.append("")

            # Current understanding
            if 'partial_understanding' in data:
                understanding = data['partial_understanding']
                lines.append("✅ Current Understanding:")
                if 'app_purpose' in understanding:
                    lines.append(f"   Purpose: {understanding['app_purpose']}")
                if 'target_users' in understanding:
                    lines.append(f"   Users: {understanding['target_users']}")
                if 'core_features' in understanding:
                    lines.append(f"   Features: {', '.join(understanding['core_features'][:3])}")
                    if len(understanding['core_features']) > 3:
                        lines.append(f"              ...and {len(understanding['core_features']) - 3} more")
                lines.append("")

            # Missing information
            if 'missing_info' in data and data['missing_info']:
                lines.append("⚠️  Missing Critical Information:")
                for info in data['missing_info']:
                    lines.append(f"   • {info}")
                lines.append("")

            # Questions for user
            if 'questions' in data and data['questions']:
                lines.append("❓ Please provide more details:")
                for i, question in enumerate(data['questions'], 1):
                    lines.append(f"   {i}. {question}")
                lines.append("")

            lines.append("💡 Tip: Provide more details about the missing information above,")
            lines.append("   and I'll create a comprehensive plan for you.")

            return "\n".join(lines)

        # Handle successful plan creation
        elif status == 'plan_created':
            lines.append("📋 Application Plan Created Successfully")
            lines.append("")
            lines.append("=" * 80)
            lines.append("")

            # Metadata
            if 'metadata' in data:
                meta = data['metadata']
                lines.append("📊 Plan Summary:")
                lines.append(f"   • Application Type: {meta.get('app_type', 'N/A')}")
                lines.append(f"   • Total Epics: {meta.get('epics_count', 0)}")
                lines.append(f"   • Total User Stories: {meta.get('total_stories', 0)}")
                lines.append(f"   • Created: {meta.get('created_at', 'N/A')}")
                lines.append("")

            # Document location
            if 'document_path' in data:
                lines.append("📁 Plan Document:")
                lines.append(f"   {data['document_path']}")
                lines.append("")

            # Validation results
            if 'validation' in data:
                validation = data['validation']
                confidence = validation.get('confidence', 0.0)
                lines.append(f"✅ Validation: {confidence:.1%} confidence")

                if validation.get('quality_assessment'):
                    qa = validation['quality_assessment']
                    lines.append(f"   • Completeness: {qa.get('completeness', 'N/A')}")
                    lines.append(f"   • Clarity: {qa.get('clarity', 'N/A')}")
                    lines.append(f"   • Actionability: {qa.get('actionability', 'N/A')}")

                if validation.get('issues'):
                    lines.append("")
                    lines.append("   ⚠️  Issues identified:")
                    for issue in validation['issues'][:3]:
                        lines.append(f"      - {issue}")
                    if len(validation['issues']) > 3:
                        lines.append(f"      ...and {len(validation['issues']) - 3} more (see document)")

                lines.append("")

            # Show plan overview
            if 'plan' in data:
                plan = data['plan']

                # Vision
                if 'vision' in plan:
                    lines.append("🎯 Vision:")
                    for line in self._wrap_text(plan['vision'], width=75, indent=3):
                        lines.append(line)
                    lines.append("")

                # Objectives
                if 'objectives' in plan and plan['objectives']:
                    lines.append("🎯 Key Objectives:")
                    for obj in plan['objectives'][:5]:
                        lines.append(f"   • {obj}")
                    if len(plan['objectives']) > 5:
                        lines.append(f"   ...and {len(plan['objectives']) - 5} more")
                    lines.append("")

                # Epics overview
                if 'epics' in plan:
                    lines.append(f"📚 Epics ({len(plan['epics'])} total):")
                    lines.append("")

                    for epic in plan['epics'][:3]:  # Show first 3 epics
                        epic_id = epic.get('id', 'N/A')
                        title = epic.get('title', 'Untitled')
                        priority = epic.get('priority', 'Medium')
                        story_count = len(epic.get('user_stories', []))

                        lines.append(f"   {epic_id}: {title}")
                        lines.append(f"   Priority: {priority} | Stories: {story_count}")

                        # Show first 2 user stories
                        for story in epic.get('user_stories', [])[:2]:
                            story_id = story.get('id', 'N/A')
                            story_title = story.get('title', 'Untitled')
                            lines.append(f"      • {story_id}: {story_title}")

                        if story_count > 2:
                            lines.append(f"      ...and {story_count - 2} more stories")
                        lines.append("")

                    if len(plan['epics']) > 3:
                        lines.append(f"   ...and {len(plan['epics']) - 3} more epics")
                        lines.append("")

                # Risks
                if 'risks' in plan and plan['risks']:
                    lines.append("⚠️  Key Risks:")
                    for risk in plan['risks'][:3]:
                        lines.append(f"   • {risk.get('description', 'N/A')} (Impact: {risk.get('impact', 'N/A')})")
                    if len(plan['risks']) > 3:
                        lines.append(f"   ...and {len(plan['risks']) - 3} more risks")
                    lines.append("")

            lines.append("=" * 80)
            lines.append("")
            lines.append("📄 Full plan with detailed user stories, acceptance criteria,")
            lines.append("   and technical notes is saved in the document above.")

            return "\n".join(lines)

        # Generic fallback for unknown status
        else:
            return self._format_generic("planning", data)

    def _format_generic(self, agent_name: str, data: Dict[str, Any]) -> str:
        """Generic formatter for unknown agent types."""
        # Strip numeric suffix from agent name (e.g., "weather_1" -> "weather")
        display_name = agent_name
        if '_' in agent_name:
            parts = agent_name.rsplit('_', 1)
            if len(parts) == 2 and parts[1].isdigit():
                display_name = parts[0]

        lines = [f"📤 {display_name.replace('_', ' ').title()} Results:"]

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
