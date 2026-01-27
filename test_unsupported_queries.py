#!/usr/bin/env python3
"""
Test script to verify unsupported queries are gracefully rejected.
Tests that "change my address" and similar queries return no agents.
"""

import asyncio
import logging
import sys
from agent_orchestrator.orchestrator import AgentOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_unsupported_queries():
    """Test that unsupported queries are correctly rejected."""
    print("=" * 80)
    print("TESTING UNSUPPORTED QUERY HANDLING")
    print("=" * 80)
    
    # Initialize orchestrator
    print("\n1. Initializing orchestrator...")
    orchestrator = AgentOrchestrator(config_path="config/orchestrator.yaml")
    await orchestrator.initialize()
    
    # Test queries that should be rejected
    unsupported_queries = [
        "i want to change my address",
        "change my address",
        "update my address please",
        "reset my password",
        "check my account balance",
        "transfer $100 to my savings",
        "I need to speak to a customer service representative",
    ]
    
    # Test queries that should work
    supported_queries = [
        "plan a trip from Manchester to Penrith",
        "what's the weather in London",
        "calculate 25 + 75",
    ]
    
    print("\n2. Testing unsupported queries (should return NO agents):")
    print("=" * 80)
    
    unsupported_results = []
    for query in unsupported_queries:
        print(f"\n🔍 Query: '{query}'")
        result = await orchestrator.process_request(query)
        
        agents_used = result.get("agents_used", [])
        success = result.get("success", False)
        response = result.get("response", "")
        
        if not agents_used and not success:
            print(f"   ✅ Correctly rejected (no agents)")
            print(f"   Response: {response[:150]}...")
            unsupported_results.append(True)
        else:
            print(f"   ❌ INCORRECTLY HANDLED")
            print(f"   Agents used: {agents_used}")
            print(f"   Success: {success}")
            unsupported_results.append(False)
    
    print("\n\n3. Testing supported queries (should return agents):")
    print("=" * 80)
    
    supported_results = []
    for query in supported_queries:
        print(f"\n🔍 Query: '{query}'")
        result = await orchestrator.process_request(query)
        
        agents_used = result.get("agents_used", [])
        success = result.get("success", False)
        
        if agents_used:
            print(f"   ✅ Agents: {', '.join(agents_used)}")
            supported_results.append(True)
        else:
            print(f"   ❌ No agents found (unexpected)")
            supported_results.append(False)
    
    # Summary
    print("\n\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    unsupported_success_rate = sum(unsupported_results) / len(unsupported_results) * 100
    supported_success_rate = sum(supported_results) / len(supported_results) * 100
    
    print(f"\nUnsupported queries correctly rejected: {sum(unsupported_results)}/{len(unsupported_results)} ({unsupported_success_rate:.0f}%)")
    print(f"Supported queries correctly handled: {sum(supported_results)}/{len(supported_results)} ({supported_success_rate:.0f}%)")
    
    overall_success = all(unsupported_results) and all(supported_results)
    
    if overall_success:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


async def main():
    """Run tests."""
    try:
        return await test_unsupported_queries()
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
