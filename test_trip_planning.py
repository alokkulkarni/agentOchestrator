#!/usr/bin/env python3
"""
Test script to verify trip planning queries are correctly routed to planning + search agents.
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

async def test_trip_planning():
    """Test trip planning query routing."""
    print("=" * 80)
    print("TESTING TRIP PLANNING AGENT ROUTING")
    print("=" * 80)
    
    # Initialize orchestrator
    print("\n1. Initializing orchestrator...")
    orchestrator = AgentOrchestrator(config_path="config/orchestrator.yaml")
    await orchestrator.initialize()
    
    # Test query
    query = "please plan me a trip by car from manchester to penrith, uk and also show me points of interest along the route."
    
    print(f"\n2. Testing query:\n   '{query}'")
    print("\n3. Expected agents: search, tavily_search, planning")
    print("   Expected mode: sequential\n")
    
    # Process request
    print("4. Processing request...\n")
    result = await orchestrator.process_request(query)
    
    # Display results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    if result.get("success"):
        agents_used = result.get("agents_used", [])
        print(f"✅ Success! Agents used: {', '.join(agents_used)}")
        
        # Check if correct agents were used
        expected_agents = {"search", "tavily_search", "planning"}
        if set(agents_used) == expected_agents:
            print("✅ Correct agents selected!")
        else:
            print(f"⚠️  Expected agents: {expected_agents}")
            print(f"   Got agents: {set(agents_used)}")
        
        # Display agent results
        print("\n5. Agent results:")
        for interaction in result.get("agent_interactions", []):
            agent_name = interaction.get("agent_name")
            status = interaction.get("status")
            print(f"   - {agent_name}: {status}")
            
            if interaction.get("result"):
                result_preview = str(interaction["result"])[:200]
                print(f"     Result: {result_preview}...")
        
        print("\n6. Final response:")
        response = result.get("response", "")
        print(f"   {response[:500]}...")
        
    else:
        print("❌ Failed!")
        error = result.get("error", "Unknown error")
        print(f"   Error: {error}")
        
        if result.get("errors"):
            print("\n   Detailed errors:")
            for err in result["errors"]:
                print(f"   - {err.get('error_type')}: {err.get('error_message')}")
    
    print("\n" + "=" * 80)
    return result.get("success", False)


async def test_additional_queries():
    """Test additional trip planning queries."""
    print("\n\n" + "=" * 80)
    print("TESTING ADDITIONAL TRIP PLANNING QUERIES")
    print("=" * 80)
    
    orchestrator = AgentOrchestrator(config_path="config/orchestrator.yaml")
    await orchestrator.initialize()
    
    test_queries = [
        "plan a trip from London to Edinburgh",
        "create an itinerary for a weekend in Paris",
        "drive from New York to Boston with stops",
    ]
    
    results = []
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        result = await orchestrator.process_request(query)
        
        if result.get("success"):
            agents = ', '.join(result.get("agents_used", []))
            print(f"   ✅ Agents: {agents}")
            results.append(True)
        else:
            print(f"   ❌ Failed: {result.get('error')}")
            results.append(False)
    
    print("\n" + "=" * 80)
    print(f"Summary: {sum(results)}/{len(results)} queries succeeded")
    print("=" * 80)
    
    return all(results)


async def main():
    """Run tests."""
    try:
        # Test main query
        success1 = await test_trip_planning()
        
        # Test additional queries
        success2 = await test_additional_queries()
        
        # Final summary
        print("\n\n" + "=" * 80)
        print("FINAL TEST SUMMARY")
        print("=" * 80)
        
        if success1 and success2:
            print("✅ All tests passed!")
            return 0
        else:
            print("❌ Some tests failed")
            return 1
            
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
