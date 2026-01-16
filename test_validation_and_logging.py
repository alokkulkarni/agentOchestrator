#!/usr/bin/env python3
"""
Test script for response validation and per-query logging.

This script tests:
1. Response validation against user query
2. Hallucination detection
3. Confidence scoring (logged but not sent to user)
4. Retry on validation failure
5. Comprehensive per-query logging
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from agent_orchestrator import Orchestrator
from agent_orchestrator.utils import QueryLogReader

# Load environment variables
load_dotenv()


async def test_basic_validation():
    """Test basic validation with a simple query."""
    print("\n" + "=" * 70)
    print("TEST 1: Basic Validation - Simple Calculator Query")
    print("=" * 70)

    orchestrator = Orchestrator(config_path="config/orchestrator.yaml")
    await orchestrator.initialize()

    try:
        result = await orchestrator.process({
            "query": "calculate 2 + 2",
            "operation": "add",
            "operands": [2, 2]
        })

        print("\nResult:")
        print(f"  Success: {result['success']}")
        print(f"  Data: {json.dumps(result.get('data', {}), indent=2)}")

        # Check for validation warning (should not be present for valid result)
        validation_warning = result.get('_metadata', {}).get('validation_warning')
        if validation_warning:
            print(f"\n⚠️  Validation Warning: {validation_warning}")
        else:
            print("\n✅ No validation warnings (response passed validation)")

        return result['success']

    finally:
        await orchestrator.cleanup()


async def test_validation_with_inconsistency():
    """Test validation with potentially inconsistent data."""
    print("\n" + "=" * 70)
    print("TEST 2: Validation - Search Query")
    print("=" * 70)

    orchestrator = Orchestrator(config_path="config/orchestrator.yaml")
    await orchestrator.initialize()

    try:
        result = await orchestrator.process({
            "query": "search for python programming tutorials",
            "max_results": 5
        })

        print("\nResult:")
        print(f"  Success: {result['success']}")

        if result['success'] and 'search' in result.get('data', {}):
            search_data = result['data']['search']
            print(f"  Results Found: {search_data.get('total_count', 0)}")

        # Check for validation metadata
        validation_warning = result.get('_metadata', {}).get('validation_warning')
        if validation_warning:
            print(f"\n⚠️  Validation Warning:")
            print(f"    Message: {validation_warning.get('message')}")
            print(f"    Hallucination: {validation_warning.get('hallucination_detected')}")
            print(f"    Issues: {validation_warning.get('issues')}")
        else:
            print("\n✅ Response passed validation")

        return result['success']

    finally:
        await orchestrator.cleanup()


async def test_query_log_inspection():
    """Test query log inspection."""
    print("\n" + "=" * 70)
    print("TEST 3: Query Log Inspection")
    print("=" * 70)

    # Check if logs directory exists
    log_dir = Path("logs/queries")
    if not log_dir.exists():
        print("❌ No query logs found. Run some queries first.")
        return False

    reader = QueryLogReader(log_dir="logs/queries")

    # Get recent queries
    recent_logs = reader.get_recent_queries(limit=5)
    print(f"\n📊 Found {len(recent_logs)} recent query logs")

    if recent_logs:
        latest_log = recent_logs[0]

        print("\n📋 Latest Query Log:")
        print(f"  Query ID: {latest_log['query_id']}")
        print(f"  Timestamp: {latest_log['timestamp']}")
        print(f"  Query: {latest_log['user_query'].get('query', 'N/A')}")

        # Show reasoning decision
        reasoning = latest_log.get('reasoning', {})
        if reasoning:
            print(f"\n  🧠 Reasoning:")
            print(f"    Mode: {reasoning.get('mode')}")
            print(f"    Method: {reasoning.get('method')}")
            print(f"    Selected Agents: {reasoning.get('selected_agents')}")
            print(f"    Confidence: {reasoning.get('confidence')}")

        # Show agent interactions
        agent_interactions = latest_log.get('agent_interactions', [])
        if agent_interactions:
            print(f"\n  ⚙️  Agent Interactions: {len(agent_interactions)}")
            for interaction in agent_interactions:
                print(f"    - {interaction['agent_name']}: "
                      f"{'✅ success' if interaction['success'] else '❌ failed'} "
                      f"({interaction['execution_time_ms']:.2f}ms)")

        # Show validation results (includes confidence score)
        validation = latest_log.get('validation', {})
        if validation:
            print(f"\n  ✓ Validation:")
            print(f"    Valid: {validation.get('is_valid')}")
            print(f"    Confidence Score: {validation.get('confidence_score', 0):.3f}")
            print(f"    Hallucination Detected: {validation.get('hallucination_detected')}")
            if validation.get('issues'):
                print(f"    Issues: {validation['issues']}")

        # Show retry attempts
        retry_attempts = latest_log.get('retry_attempts', [])
        if retry_attempts:
            print(f"\n  🔄 Retry Attempts: {len(retry_attempts)}")
            for attempt in retry_attempts:
                print(f"    Attempt {attempt['attempt_number']}: {attempt['reason']}")

        # Show timing
        timing = latest_log.get('timing', {})
        if timing:
            print(f"\n  ⏱️  Timing:")
            print(f"    Duration: {timing.get('total_duration_ms', 0):.2f}ms")

    # Get statistics
    print("\n📈 Query Log Statistics:")
    stats = reader.get_stats()
    print(f"  Total Queries: {stats['total_queries']}")
    print(f"  Success Rate: {stats['success_rate']:.1%}")
    print(f"  Avg Duration: {stats['avg_duration_ms']:.2f}ms")
    print(f"  Avg Confidence: {stats['avg_confidence']:.3f}")
    print(f"  Hallucination Rate: {stats['hallucination_rate']:.1%}")
    print(f"  Retry Rate: {stats['retry_rate']:.1%}")

    return True


async def test_confidence_not_in_response():
    """Verify confidence score is NOT sent to user (only in logs)."""
    print("\n" + "=" * 70)
    print("TEST 4: Verify Confidence Score Not in User Response")
    print("=" * 70)

    orchestrator = Orchestrator(config_path="config/orchestrator.yaml")
    await orchestrator.initialize()

    try:
        result = await orchestrator.process({
            "query": "calculate 10 + 20",
            "operation": "add",
            "operands": [10, 20]
        })

        print("\nChecking response for confidence score...")

        # Convert response to JSON string to search for 'confidence'
        response_str = json.dumps(result)

        # Check if confidence is NOT in the response
        # (It should only be in logs, not returned to user)
        if 'confidence_score' in response_str or 'confidence score' in response_str.lower():
            print("❌ FAILED: Confidence score found in user response!")
            print(f"   This should only be in logs, not sent to user.")
            return False
        else:
            print("✅ PASSED: Confidence score is NOT in user response")
            print("   (It is only logged internally)")

        # Now check that it IS in the log file
        reader = QueryLogReader(log_dir="logs/queries")
        recent_logs = reader.get_recent_queries(limit=1)

        if recent_logs:
            latest_log = recent_logs[0]
            validation = latest_log.get('validation', {})
            confidence_score = validation.get('confidence_score')

            if confidence_score is not None:
                print(f"✅ PASSED: Confidence score found in log file: {confidence_score:.3f}")
                return True
            else:
                print("⚠️  WARNING: Confidence score not found in log file")
                return False
        else:
            print("⚠️  WARNING: No log file found to verify")
            return False

    finally:
        await orchestrator.cleanup()


async def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("VALIDATION AND LOGGING TESTS")
    print("=" * 70)

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\n⚠️  WARNING: ANTHROPIC_API_KEY not set.")
        print("AI-based validation will be limited. Rule-based validation will still work.")
        print()

    results = []

    # Run tests
    try:
        results.append(("Basic Validation", await test_basic_validation()))
        results.append(("Search Validation", await test_validation_with_inconsistency()))
        results.append(("Log Inspection", await test_query_log_inspection()))
        results.append(("Confidence Not in Response", await test_confidence_not_in_response()))

    except Exception as e:
        print(f"\n❌ Test Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
