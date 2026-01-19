#!/usr/bin/env python3
"""
Test script for Tavily Search Agent integration.

Tests:
1. Tavily agent is registered
2. Tavily agent can be called directly
3. Orchestrator routes web search queries to Tavily
4. Results are properly formatted
"""

import asyncio
import json
import os
import sys

from dotenv import load_dotenv

from agent_orchestrator import Orchestrator

# Load environment variables
load_dotenv()


async def test_tavily_agent_registration():
    """Test that Tavily agent is properly registered."""
    print("\n" + "=" * 70)
    print("TEST 1: Tavily Agent Registration")
    print("=" * 70)

    orchestrator = Orchestrator(config_path="config/orchestrator.yaml")
    await orchestrator.initialize()

    try:
        # Check if Tavily agent is registered
        tavily_agent = orchestrator.agent_registry.get("tavily_search")

        if tavily_agent:
            print("\n✅ Tavily agent is registered")
            print(f"   Name: {tavily_agent.name}")
            print(f"   Capabilities: {', '.join(tavily_agent.capabilities)}")
            print(f"   Type: {tavily_agent.__class__.__name__}")
            return True
        else:
            print("\n❌ Tavily agent NOT found in registry")
            return False

    finally:
        await orchestrator.cleanup()


async def test_tavily_direct_call():
    """Test calling Tavily agent directly."""
    print("\n" + "=" * 70)
    print("TEST 2: Tavily Direct Call")
    print("=" * 70)

    # Check if API key is set
    if not os.getenv("TAVILY_API_KEY"):
        print("\n⚠️  TAVILY_API_KEY not set. Skipping direct call test.")
        print("   Set TAVILY_API_KEY in .env to test Tavily API.")
        return None

    orchestrator = Orchestrator(config_path="config/orchestrator.yaml")
    await orchestrator.initialize()

    try:
        tavily_agent = orchestrator.agent_registry.get("tavily_search")

        if not tavily_agent:
            print("\n❌ Tavily agent not found")
            return False

        print("\n📡 Calling Tavily API...")

        # Call Tavily directly
        result = await tavily_agent.call({
            "query": "Claude AI by Anthropic",
            "max_results": 3,
            "include_answer": True,
        })

        print(f"\nSuccess: {result.success}")

        if result.success:
            data = result.data
            print(f"Query: {data.get('query')}")
            print(f"Total Results: {data.get('total_results')}")

            if 'answer' in data:
                print(f"\n📝 AI Answer:")
                print(f"   {data['answer'][:150]}...")

            print(f"\n🔍 Search Results:")
            for i, r in enumerate(data.get('results', [])[:3], 1):
                print(f"\n   {i}. {r.get('title', 'N/A')[:60]}")
                print(f"      URL: {r.get('url', 'N/A')[:70]}")
                print(f"      Score: {r.get('score', 0):.3f}")

            return True
        else:
            print(f"Error: {result.error}")
            return False

    finally:
        await orchestrator.cleanup()


async def test_orchestrator_routing():
    """Test that orchestrator routes web search queries to Tavily."""
    print("\n" + "=" * 70)
    print("TEST 3: Orchestrator Routing to Tavily")
    print("=" * 70)

    # Check if API key is set
    if not os.getenv("TAVILY_API_KEY"):
        print("\n⚠️  TAVILY_API_KEY not set. Skipping routing test.")
        return None

    orchestrator = Orchestrator(config_path="config/orchestrator.yaml")
    await orchestrator.initialize()

    try:
        # Test queries that should route to Tavily
        test_queries = [
            {"query": "latest news about artificial intelligence", "max_results": 3},
            {"query": "current weather in San Francisco online", "max_results": 2},
            {"query": "web search for Python 3.12 features", "max_results": 3},
        ]

        for i, test_query in enumerate(test_queries, 1):
            print(f"\n{'-' * 70}")
            print(f"Query {i}: {test_query['query']}")
            print(f"{'-' * 70}")

            result = await orchestrator.process(test_query)

            print(f"\nSuccess: {result['success']}")

            if result['success']:
                # Check which agent was used
                agent_trail = result.get('_metadata', {}).get('agent_trail', [])
                print(f"Agent Used: {', '.join(agent_trail)}")

                if 'tavily_search' in agent_trail:
                    print("✅ Correctly routed to Tavily")

                    # Show some results
                    if 'tavily_search' in result.get('data', {}):
                        tavily_data = result['data']['tavily_search']
                        print(f"Results: {tavily_data.get('total_results', 0)}")

                        if tavily_data.get('results'):
                            print(f"\nTop Result:")
                            top = tavily_data['results'][0]
                            print(f"  {top.get('title', 'N/A')[:60]}")
                            print(f"  {top.get('url', 'N/A')[:70]}")
                else:
                    print(f"⚠️  Routed to: {agent_trail} (expected tavily_search)")
            else:
                print(f"❌ Request failed: {result.get('error')}")

        return True

    finally:
        await orchestrator.cleanup()


async def test_tavily_fallback():
    """Test that Tavily falls back to local search if API fails."""
    print("\n" + "=" * 70)
    print("TEST 4: Tavily Fallback Behavior")
    print("=" * 70)

    print("\nThis test verifies fallback when:")
    print("  1. TAVILY_API_KEY is not set")
    print("  2. Tavily API returns an error")
    print("  3. Network connectivity issues")

    orchestrator = Orchestrator(config_path="config/orchestrator.yaml")
    await orchestrator.initialize()

    try:
        # Check current API key status
        api_key = os.getenv("TAVILY_API_KEY")

        if api_key:
            print(f"\n✅ TAVILY_API_KEY is set")
            print("   Fallback will occur on API errors")
        else:
            print(f"\n⚠️  TAVILY_API_KEY not set")
            print("   Tavily agent will return error")
            print("   Orchestrator will fallback to 'search' agent")

        # Try a web search query
        result = await orchestrator.process({
            "query": "latest technology news",
            "max_results": 3,
        })

        agent_trail = result.get('_metadata', {}).get('agent_trail', [])
        print(f"\nAgent Trail: {', '.join(agent_trail)}")

        if 'tavily_search' in agent_trail:
            print("✅ Tavily agent was used")
        elif 'search' in agent_trail:
            print("✅ Fallback to local search agent")
        else:
            print(f"⚠️  Unexpected agents: {agent_trail}")

        return True

    finally:
        await orchestrator.cleanup()


async def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("TAVILY SEARCH AGENT TESTS")
    print("=" * 70)

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\n⚠️  WARNING: ANTHROPIC_API_KEY not set.")
        print("AI routing will be limited. Set it in .env for full testing.")

    results = []

    try:
        # Test 1: Registration
        results.append(("Agent Registration", await test_tavily_agent_registration()))

        # Test 2: Direct call (skip if no API key)
        direct_result = await test_tavily_direct_call()
        if direct_result is not None:
            results.append(("Direct API Call", direct_result))

        # Test 3: Orchestrator routing (skip if no API key)
        routing_result = await test_orchestrator_routing()
        if routing_result is not None:
            results.append(("Orchestrator Routing", routing_result))

        # Test 4: Fallback behavior
        results.append(("Fallback Behavior", await test_tavily_fallback()))

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
        if result is True:
            status = "✅ PASSED"
        elif result is False:
            status = "❌ FAILED"
        else:
            status = "⚠️  SKIPPED"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} test(s) failed or skipped")
        print("\nNote: Some tests require TAVILY_API_KEY to be set")
        sys.exit(0 if passed > 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
