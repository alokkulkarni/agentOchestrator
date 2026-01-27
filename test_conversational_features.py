#!/usr/bin/env python3
"""
Test script to demonstrate the new conversational features of the orchestrator.

This script demonstrates:
1. Natural follow-up questions after responses
2. Context-aware conversation flow
3. Graceful session closing when user says "done for the day"
4. Friendly error handling with conversational tone
"""

import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_orchestrator.formatting.conversational_wrapper import (
    ConversationalWrapper,
    ConversationState,
)


def test_conversational_wrapper():
    """Test the conversational wrapper with various scenarios."""
    print("=" * 80)
    print("Testing Conversational Wrapper")
    print("=" * 80)
    print()
    
    wrapper = ConversationalWrapper()
    
    # Test 1: Weather query with follow-up
    print("Test 1: Weather Query")
    print("-" * 80)
    original_response = """📍 Weather for New York, United States

🌡️  Temperature: 15°C
💨 Feels like: 13°C
☁️  Conditions: Partly Cloudy
💧 Humidity: 65%
🌬️  Wind: 5.2 m/s"""
    
    enhanced = wrapper.wrap_response(
        original_response=original_response,
        query="What's the weather in New York?",
        session_id="test_session_1",
        is_error=False
    )
    print(enhanced)
    print("\n")
    
    # Test 2: Calculation with follow-up
    print("Test 2: Calculation Query")
    print("-" * 80)
    original_response = "🔢 25 + 37 = 62"
    
    enhanced = wrapper.wrap_response(
        original_response=original_response,
        query="Calculate 25 plus 37",
        session_id="test_session_2",
        is_error=False
    )
    print(enhanced)
    print("\n")
    
    # Test 3: User saying "done for the day"
    print("Test 3: User Ending Session")
    print("-" * 80)
    original_response = "All tasks completed successfully."
    
    enhanced = wrapper.wrap_response(
        original_response=original_response,
        query="I'm done for the day, thanks!",
        session_id="test_session_3",
        is_error=False
    )
    print(enhanced)
    print("\n")
    
    # Test 4: Error handling with conversational tone
    print("Test 4: Error Response")
    print("-" * 80)
    original_response = "Security validation failed: Invalid input detected"
    
    enhanced = wrapper.wrap_response(
        original_response=original_response,
        query="What's the weather?",
        session_id="test_session_4",
        is_error=True
    )
    print(enhanced)
    print("\n")
    
    # Test 5: Multiple requests in same session
    print("Test 5: Multiple Requests in Same Session")
    print("-" * 80)
    session_id = "test_session_5"
    state = wrapper.state_manager.get_or_create(session_id)
    
    # Request 1
    print("Request 1:")
    response1 = wrapper.wrap_response(
        original_response="🔢 10 + 5 = 15",
        query="Calculate 10 plus 5",
        session_id=session_id,
        is_error=False
    )
    print(response1)
    print()
    
    # Request 2
    print("Request 2:")
    response2 = wrapper.wrap_response(
        original_response="🔢 15 * 2 = 30",
        query="Multiply that by 2",
        session_id=session_id,
        is_error=False
    )
    print(response2)
    print()
    
    # Request 3 - After several requests
    print("Request 3:")
    response3 = wrapper.wrap_response(
        original_response="🔢 30 - 10 = 20",
        query="Subtract 10",
        session_id=session_id,
        is_error=False
    )
    print(response3)
    print()
    
    # Request 4 - More than 3 requests
    print("Request 4:")
    response4 = wrapper.wrap_response(
        original_response="🔢 20 / 4 = 5",
        query="Divide by 4",
        session_id=session_id,
        is_error=False
    )
    print(response4)
    print()
    
    # Final request - User done
    print("Final Request (User Done):")
    final_response = wrapper.wrap_response(
        original_response="Task completed.",
        query="That's all, thanks!",
        session_id=session_id,
        is_error=False
    )
    print(final_response)
    print()
    
    # Test 6: Different exit phrases
    print("Test 6: Various Exit Phrases")
    print("-" * 80)
    
    exit_phrases = [
        "I'm done for the day",
        "That's all for today",
        "Nothing else, thanks",
        "Goodbye!",
        "All set, thanks",
        "We're done here",
    ]
    
    for i, phrase in enumerate(exit_phrases, 1):
        print(f"Exit phrase {i}: '{phrase}'")
        is_closing = wrapper._is_closing_intent(phrase)
        print(f"Detected as closing intent: {is_closing}")
        if is_closing:
            response = wrapper._create_closing_response(
                original_response="",
                session_id=f"exit_test_{i}"
            )
            print(response)
        print()


def test_conversation_state():
    """Test conversation state tracking."""
    print("\n")
    print("=" * 80)
    print("Testing Conversation State Tracking")
    print("=" * 80)
    print()
    
    state = ConversationState("test_session")
    
    # Simulate multiple interactions
    interactions = [
        ("What's the weather in London?", "success"),
        ("Calculate 42 times 3", "success"),
        ("Search for Python tutorials", "success"),
        ("Invalid request!", "error"),
    ]
    
    for query, response_type in interactions:
        state.update(query, response_type)
        print(f"Query: {query}")
        print(f"  Response Type: {response_type}")
        print(f"  Request Count: {state.request_count}")
        print(f"  Last Topic: {state.last_query_topic}")
        print()
    
    print(f"Total interactions: {len(state.interaction_history)}")
    print(f"Interaction history:")
    for i, interaction in enumerate(state.interaction_history, 1):
        print(f"  {i}. [{interaction['type']}] {interaction['query'][:50]}...")


if __name__ == "__main__":
    print("\n🤖 Conversational Orchestrator Feature Demo\n")
    
    test_conversational_wrapper()
    test_conversation_state()
    
    print("\n" + "=" * 80)
    print("✅ All tests completed!")
    print("=" * 80)
    print()
    print("💡 Key Features Demonstrated:")
    print("  ✓ Natural follow-up questions after responses")
    print("  ✓ Context-aware conversation based on query topic")
    print("  ✓ Graceful session closing detection")
    print("  ✓ Friendly error handling")
    print("  ✓ Session state tracking across multiple requests")
    print("  ✓ Adaptive prompts after several interactions")
    print()
