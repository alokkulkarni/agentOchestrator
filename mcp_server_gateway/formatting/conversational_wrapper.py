"""
Conversational wrapper for making orchestrator responses more human-like and engaging.

This module enhances responses with:
- Natural follow-up questions
- Context-aware conversation flow
- Graceful session closing
- Friendly tone while maintaining professionalism
"""

import logging
import re
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ConversationState:
    """Tracks conversation state across requests in a session."""
    
    def __init__(self, session_id: str):
        """
        Initialize conversation state for a session.
        
        Args:
            session_id: Unique session identifier
        """
        self.session_id = session_id
        self.request_count = 0
        self.last_request_time = None
        self.last_query_topic = None
        self.user_preferences = {}
        self.interaction_history = []
        
    def update(self, query: str, response_type: str):
        """Update conversation state with new interaction."""
        self.request_count += 1
        self.last_request_time = datetime.utcnow()
        self.last_query_topic = self._extract_topic(query)
        self.interaction_history.append({
            "query": query,
            "type": response_type,
            "timestamp": self.last_request_time.isoformat()
        })
        
    def _extract_topic(self, query: str) -> Optional[str]:
        """Extract the main topic/intent from query."""
        query_lower = query.lower()
        
        # Topic keywords
        topics = {
            "weather": ["weather", "temperature", "forecast", "rain", "sunny"],
            "calculation": ["calculate", "compute", "add", "subtract", "multiply", "divide"],
            "search": ["search", "find", "look up", "research"],
            "data": ["data", "aggregate", "analyze", "process", "filter"],
            "planning": ["plan", "schedule", "organize"],
            "tech": ["technology", "tech", "software", "insights"],
        }
        
        for topic, keywords in topics.items():
            if any(keyword in query_lower for keyword in keywords):
                return topic
                
        return "general"


class ConversationStateManager:
    """Manages conversation states across multiple sessions."""
    
    def __init__(self):
        self.sessions: Dict[str, ConversationState] = {}
        
    def get_or_create(self, session_id: str) -> ConversationState:
        """Get existing or create new conversation state."""
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationState(session_id)
        return self.sessions[session_id]
        
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove sessions older than specified hours."""
        now = datetime.utcnow()
        to_remove = []
        
        for session_id, state in self.sessions.items():
            if state.last_request_time:
                age_hours = (now - state.last_request_time).total_seconds() / 3600
                if age_hours > max_age_hours:
                    to_remove.append(session_id)
                    
        for session_id in to_remove:
            del self.sessions[session_id]
            logger.info(f"Cleaned up old session: {session_id}")


class ConversationalWrapper:
    """
    Wraps orchestrator responses with conversational elements.
    
    Makes responses more human-like while maintaining:
    - Existing guardrails and constraints
    - Security validation
    - Output formatting
    - Error handling
    """
    
    def __init__(self):
        """Initialize conversational wrapper."""
        self.state_manager = ConversationStateManager()
        
        # Conversational templates
        self.follow_up_templates = {
            "weather": [
                "Would you like weather information for another location?",
                "Is there anything else I can help you with today?",
                "Need weather forecasts for any other cities?"
            ],
            "calculation": [
                "Need help with any other calculations?",
                "Can I assist with any other math problems?",
                "What else can I help you compute?"
            ],
            "search": [
                "Would you like me to search for something else?",
                "Need more information on a different topic?",
                "Can I help you find anything else?"
            ],
            "data": [
                "Would you like me to process any other data?",
                "Need additional data analysis or aggregation?",
                "Can I help with any other data operations?"
            ],
            "general": [
                "What else can I help you with?",
                "Is there anything else you'd like to know?",
                "How else can I assist you today?"
            ],
            "error": [
                "Let me try a different approach. What would you like help with?",
                "I'm here to help. What else can I assist you with?",
            ]
        }
        
        self.closing_phrases = [
            "Great working with you today! Have a wonderful rest of your day!",
            "Thank you for using the orchestrator! Have a great day ahead!",
            "It's been a pleasure assisting you today. Take care!",
            "Excellent! If you need anything else later, I'll be here. Have a great day!",
            "All done! Wishing you a productive rest of your day!",
        ]
        
        self.next_steps_templates = {
            "weather": "💡 **Next Steps**: You can ask for weather in other cities or switch to different tasks like calculations, searches, or data processing.",
            "calculation": "💡 **Next Steps**: Feel free to ask for more calculations, or I can help with weather, searches, or data analysis.",
            "search": "💡 **Next Steps**: I can search for more topics, or assist with weather, calculations, or data operations.",
            "data": "💡 **Next Steps**: I can process more data, or help with other tasks like weather queries, calculations, or searches.",
            "general": "💡 **Next Steps**: I'm ready to help with weather, calculations, searches, data processing, and more!"
        }
        
    def wrap_response(
        self,
        original_response: str,
        query: str,
        session_id: Optional[str] = None,
        is_error: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Wrap response with conversational elements.
        
        Args:
            original_response: The original response text
            query: The user's query
            session_id: Optional session ID for state tracking
            is_error: Whether this is an error response
            metadata: Optional metadata about the response
            
        Returns:
            Enhanced response with conversational elements
        """
        # Detect if user is done or wants to exit
        if self._is_closing_intent(query):
            return self._create_closing_response(original_response, session_id)
            
        # Update conversation state if session tracking is enabled
        conversation_state = None
        if session_id:
            conversation_state = self.state_manager.get_or_create(session_id)
            response_type = "error" if is_error else "success"
            conversation_state.update(query, response_type)
            
        # Build enhanced response
        enhanced_parts = []
        
        # Original response content
        enhanced_parts.append(original_response)
        
        # Add separator
        enhanced_parts.append("\n" + "─" * 60 + "\n")
        
        # Add follow-up question based on context
        if not is_error:
            follow_up = self._get_follow_up_question(query, conversation_state)
            enhanced_parts.append(f"💬 {follow_up}")
        else:
            # For errors, be more supportive
            follow_up = self._get_follow_up_question(query, conversation_state, is_error=True)
            enhanced_parts.append(f"💬 {follow_up}")
            
        return "\n".join(enhanced_parts)
        
    def _is_closing_intent(self, query: str) -> bool:
        """Detect if user wants to close/end the conversation."""
        query_lower = query.lower().strip()
        
        closing_patterns = [
            r'\b(done|finished|complete|through)\b.*\b(day|today)\b',
            r'\b(that\'?s? all|all done|no more|nothing else)\b',
            r'\b(goodbye|bye|see you|farewell|signing off)\b',
            r'\b(end|stop|quit|exit)\b',
            r'\b(i\'?m done|we\'?re done|all set)\b',
            r'\bthanks?,? (that\'?s? all|i\'?m good|i\'?m done)\b',
        ]
        
        return any(re.search(pattern, query_lower) for pattern in closing_patterns)
        
    def _create_closing_response(
        self,
        original_response: str,
        session_id: Optional[str] = None
    ) -> str:
        """Create a graceful closing response."""
        parts = []
        
        # Include original response if it's not just an acknowledgment
        if original_response and len(original_response) > 20:
            parts.append(original_response)
            parts.append("\n" + "─" * 60 + "\n")
        
        # Session summary if available
        if session_id:
            state = self.state_manager.sessions.get(session_id)
            if state and state.request_count > 1:
                parts.append(f"📊 **Session Summary**: We completed {state.request_count} requests together today.")
                parts.append("")
        
        # Friendly closing
        import random
        closing = random.choice(self.closing_phrases)
        parts.append(f"👋 {closing}")
        
        return "\n".join(parts)
        
    def _get_follow_up_question(
        self,
        query: str,
        conversation_state: Optional[ConversationState] = None,
        is_error: bool = False
    ) -> str:
        """Generate contextual follow-up question."""
        import random
        
        if is_error:
            return random.choice(self.follow_up_templates["error"])
        
        # Determine topic from query or conversation state
        topic = "general"
        if conversation_state and conversation_state.last_query_topic:
            topic = conversation_state.last_query_topic
        else:
            # Extract topic from current query
            state = ConversationState("temp")
            topic = state._extract_topic(query)
            
        # Get appropriate follow-up template
        templates = self.follow_up_templates.get(topic, self.follow_up_templates["general"])
        
        # Add variety based on request count
        if conversation_state and conversation_state.request_count > 3:
            # After several requests, be more encouraging about wrapping up
            return "I've been happy to help! Would you like to continue with more requests, or are you all set for now?"
            
        return random.choice(templates)
        
    def add_next_steps(
        self,
        response: str,
        query: str,
        conversation_state: Optional[ConversationState] = None
    ) -> str:
        """Add helpful next steps suggestion."""
        topic = "general"
        if conversation_state and conversation_state.last_query_topic:
            topic = conversation_state.last_query_topic
        else:
            state = ConversationState("temp")
            topic = state._extract_topic(query)
            
        next_steps = self.next_steps_templates.get(topic, self.next_steps_templates["general"])
        
        return f"{response}\n\n{next_steps}"


# Global instance for reuse
_global_wrapper = None


def get_conversational_wrapper() -> ConversationalWrapper:
    """Get or create global conversational wrapper instance."""
    global _global_wrapper
    if _global_wrapper is None:
        _global_wrapper = ConversationalWrapper()
    return _global_wrapper
