# Conversational Orchestrator Feature

## Overview

The orchestrator now includes a **conversational layer** that makes responses more human-like and engaging while maintaining all existing guardrails, security validation, and constraints.

## New Features

### 1. **Natural Follow-Up Questions**
After responding to any query, the orchestrator now asks contextual follow-up questions based on the topic:
- Weather queries: "Would you like weather information for another location?"
- Calculations: "Need help with any other calculations?"
- Searches: "Would you like me to search for something else?"
- Data operations: "Would you like me to process any other data?"
- General: "What else can I help you with?"

### 2. **Context-Aware Conversation Flow**
The orchestrator tracks conversation state across a session and adapts responses:
- Remembers the number of requests in a session
- Detects the topic/intent of queries
- After several requests (>3), provides more encouraging wrap-up prompts
- Maintains interaction history for better context

### 3. **Graceful Session Closing**
The orchestrator detects when users want to end the conversation and responds appropriately:

**Detected closing phrases:**
- "I'm done for the day"
- "That's all for today"
- "Nothing else, thanks"
- "Goodbye!" / "Bye"
- "All set" / "We're done"
- "That's all"

**Closing response includes:**
- Session summary (if multiple requests were made)
- Friendly farewell message
- Natural closing tone

### 4. **Friendly Error Handling**
Error responses now include conversational elements:
- Supportive tone when errors occur
- Helpful follow-up questions to get back on track
- Maintains professionalism while being empathetic

### 5. **Session State Tracking**
The system tracks:
- Number of requests per session
- Last query topic/intent
- Interaction history
- Timing of requests
- User preferences (extensible)

## Architecture

### Components

#### 1. **ConversationalWrapper**
Main class that wraps responses with conversational elements.

**Location:** `agent_orchestrator/formatting/conversational_wrapper.py`

**Key Methods:**
- `wrap_response()`: Enhances responses with follow-up questions
- `_is_closing_intent()`: Detects when user wants to close session
- `_create_closing_response()`: Creates graceful closing messages
- `_get_follow_up_question()`: Generates context-aware follow-ups

#### 2. **ConversationState**
Tracks state for a single conversation session.

**Tracks:**
- Request count
- Last query topic
- Interaction history
- Last request timestamp
- User preferences

#### 3. **ConversationStateManager**
Manages multiple conversation sessions and cleanup.

**Features:**
- Creates and retrieves session states
- Automatic cleanup of old sessions (>24 hours)
- Session isolation

### Integration Points

The conversational wrapper is integrated into the orchestrator at three key points:

1. **Successful responses** (after validation passes)
2. **Warning responses** (validation failed but returning best effort)
3. **Error responses** (security errors, reasoning errors, exceptions)

## Usage

### In Orchestrator Code

The conversational wrapper is automatically applied to all responses:

```python
# Success case
formatted_text = self.response_formatter.format_response(agent_data)
formatted_text = self.conversational_wrapper.wrap_response(
    original_response=formatted_text,
    query=query_text,
    session_id=session_id,
    is_error=False,
    metadata=output.get("_metadata")
)
output["formatted_text"] = formatted_text
```

### Session ID Management

Session IDs are automatically managed through the existing RequestContext:
```python
session_id = get_session_id()  # From observability context
```

### Standalone Usage

You can also use the conversational wrapper independently:

```python
from agent_orchestrator.formatting import get_conversational_wrapper

wrapper = get_conversational_wrapper()

enhanced_response = wrapper.wrap_response(
    original_response="Weather data here...",
    query="What's the weather?",
    session_id="my_session_123",
    is_error=False
)
```

## Configuration

### Customization Options

The conversational wrapper is designed to be extensible. You can customize:

1. **Follow-up templates** - Edit templates in `ConversationalWrapper.__init__`
2. **Closing phrases** - Modify `closing_phrases` list
3. **Next steps templates** - Update `next_steps_templates` dict
4. **Topic detection** - Enhance `_extract_topic()` method
5. **Session cleanup** - Adjust `max_age_hours` in cleanup method

### Disable Conversational Features

To disable conversational features without removing the code, you can:

1. Bypass the wrapper in orchestrator.py:
```python
# Instead of wrapping:
output["formatted_text"] = formatted_text  # Direct assignment
```

2. Or create a flag in config:
```yaml
# orchestrator.yaml
enable_conversational_mode: false
```

## Examples

### Example 1: Weather Query
```
User: What's the weather in New York?

Response:
📍 Weather for New York, United States
🌡️  Temperature: 15°C
☁️  Conditions: Partly Cloudy
💧 Humidity: 65%

────────────────────────────────────────────────────────────
💬 Would you like weather information for another location?
```

### Example 2: Multiple Calculations
```
User: Calculate 10 plus 5
Response:
🔢 10 + 5 = 15
────────────────────────────────────────────────────────────
💬 Need help with any other calculations?

User: Multiply that by 2
Response:
🔢 Result: 30
────────────────────────────────────────────────────────────
💬 Can I assist with any other math problems?

User: That's all for today
Response:
📊 Session Summary: We completed 2 requests together today.
👋 Great working with you today! Have a wonderful rest of your day!
```

### Example 3: Error with Recovery
```
User: [Invalid input]
Response:
Security validation failed: Invalid input detected
────────────────────────────────────────────────────────────
💬 I'm here to help. What else can I assist you with?
```

## Testing

### Run Feature Tests
```bash
python3 test_conversational_features.py
```

This test script demonstrates:
- Natural follow-up questions
- Context-aware responses
- Session closing detection
- Friendly error handling
- Multi-request session flow

### Integration Testing

Test with the interactive orchestrator:
```bash
python3 test_orchestrator_interactive.py
```

Try these scenarios:
1. Make a query → observe follow-up question
2. Make multiple queries → notice adaptive prompts
3. Say "I'm done for the day" → see graceful closing
4. Trigger an error → observe friendly error handling

## Guardrails and Constraints

### Maintained Features
All existing features remain unchanged:
- ✅ Security validation
- ✅ Input/output validation
- ✅ Response hallucination detection
- ✅ Retry logic with fallback
- ✅ Circuit breaker patterns
- ✅ Metrics and observability
- ✅ Cost tracking
- ✅ Tracing and logging
- ✅ Schema validation

### New Constraints
- Session states are automatically cleaned up after 24 hours
- Conversational elements are added to `formatted_text` only
- Original response data remains unchanged
- Metadata is preserved and enhanced

## Performance Impact

### Minimal Overhead
- Conversation state tracking: O(1) operations
- Follow-up generation: < 1ms per response
- Regex pattern matching for closing detection: < 1ms
- No external API calls
- No database queries

### Memory Usage
- Per-session state: ~1-2 KB
- Automatic cleanup prevents memory leaks
- History limited to last 1000 execution records (existing)

## Future Enhancements

Potential improvements:
1. **Personalization** - Learn user preferences over time
2. **Multi-language support** - Detect and respond in user's language
3. **Sentiment analysis** - Adapt tone based on user sentiment
4. **Context carryover** - Reference previous interactions naturally
5. **Smart suggestions** - Proactive recommendations based on patterns
6. **Voice-friendly responses** - Optimize for voice assistants
7. **Configurable personality** - Allow different conversational styles

## Troubleshooting

### Issue: Follow-up questions not appearing
**Solution:** Check that `formatted_text` is being used in your client code.

### Issue: Session state not persisting
**Solution:** Ensure `session_id` is being passed through RequestContext correctly.

### Issue: Wrong follow-up questions
**Solution:** Review topic detection in `_extract_topic()` method and add keywords.

### Issue: Closing intent not detected
**Solution:** Add new patterns to `closing_patterns` regex list.

## API Reference

### ConversationalWrapper

#### `wrap_response()`
```python
def wrap_response(
    self,
    original_response: str,
    query: str,
    session_id: Optional[str] = None,
    is_error: bool = False,
    metadata: Optional[Dict[str, Any]] = None
) -> str
```

Wraps a response with conversational elements.

**Parameters:**
- `original_response`: The original response text
- `query`: The user's query
- `session_id`: Optional session ID for state tracking
- `is_error`: Whether this is an error response
- `metadata`: Optional response metadata

**Returns:** Enhanced response with conversational elements

### ConversationState

#### `update()`
```python
def update(self, query: str, response_type: str)
```

Updates conversation state with new interaction.

**Parameters:**
- `query`: The user's query
- `response_type`: Type of response ("success" or "error")

### ConversationStateManager

#### `get_or_create()`
```python
def get_or_create(self, session_id: str) -> ConversationState
```

Gets existing or creates new conversation state.

**Parameters:**
- `session_id`: Unique session identifier

**Returns:** ConversationState instance

#### `cleanup_old_sessions()`
```python
def cleanup_old_sessions(self, max_age_hours: int = 24)
```

Removes sessions older than specified hours.

**Parameters:**
- `max_age_hours`: Maximum age in hours (default: 24)

## License

This feature is part of the Agent Orchestrator project and follows the same license terms.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review test cases in `test_conversational_features.py`
3. Examine the source code in `conversational_wrapper.py`
4. Open an issue on the project repository
