#!/usr/bin/env python3
"""
Test script for Orchestrator with Model Gateway integration.

Tests that the orchestrator can successfully use the gateway for AI reasoning.
"""

import asyncio
import os
import sys

sys.path.insert(0, '.')

from agent_orchestrator import Orchestrator


async def test_orchestrator_with_gateway():
    """Test orchestrator using Model Gateway."""
    print("\n" + "="*70)
    print("Testing Orchestrator with Model Gateway")
    print("="*70)

    try:
        # Initialize orchestrator with gateway config
        print("\n1. Initializing orchestrator with gateway configuration...")
        orchestrator = Orchestrator(
            config_path="config/orchestrator.gateway.yaml"
        )
        await orchestrator.initialize()
        print("✅ Orchestrator initialized successfully")

        # Test case 1: Calculator operation
        print("\n" + "="*70)
        print("2. Testing calculator operation through gateway...")
        print("="*70)

        calc_input = {
            "query": "Calculate 45 + 55",
            "operation": "add",
            "numbers": [45, 55]
        }

        result = await orchestrator.process(calc_input)

        if result.get("success"):
            print("✅ Calculator operation successful")
            print(f"   Agent: {result.get('agent_name', 'N/A')}")

            agent_data = result.get("agent_result", {})
            if isinstance(agent_data, dict):
                calc_result = agent_data.get("result")
                print(f"   Result: {calc_result}")
                print(f"   Reasoning: {result.get('reasoning', 'N/A')[:100]}")

            if calc_result == 100:
                print("✅ Calculation result is correct (100)")
                test1_pass = True
            else:
                print(f"❌ Calculation result incorrect (expected 100, got {calc_result})")
                test1_pass = False
        else:
            print(f"❌ Calculator operation failed: {result.get('error')}")
            test1_pass = False

        # Test case 2: Search operation
        print("\n" + "="*70)
        print("3. Testing search operation through gateway...")
        print("="*70)

        search_input = {
            "query": "Find Python programming documents",
            "keywords": ["python", "programming"],
            "max_results": 3
        }

        result = await orchestrator.process(search_input)

        if result.get("success"):
            print("✅ Search operation successful")
            print(f"   Agent: {result.get('agent_name', 'N/A')}")

            agent_data = result.get("agent_result", {})
            if isinstance(agent_data, dict):
                total = agent_data.get("total_count", 0)
                print(f"   Results: {total} documents found")
                print(f"   Reasoning: {result.get('reasoning', 'N/A')[:100]}")

            test2_pass = total > 0
            if test2_pass:
                print(f"✅ Search returned {total} results")
            else:
                print("❌ Search returned no results")
        else:
            print(f"❌ Search operation failed: {result.get('error')}")
            test2_pass = False

        # Summary
        print("\n" + "="*70)
        print("Test Summary")
        print("="*70)
        print(f"  Calculator Test: {'✅ PASS' if test1_pass else '❌ FAIL'}")
        print(f"  Search Test: {'✅ PASS' if test2_pass else '❌ FAIL'}")
        print("="*70 + "\n")

        if test1_pass and test2_pass:
            print("✅ All orchestrator-gateway integration tests passed!")
            return 0
        else:
            print("❌ Some orchestrator-gateway integration tests failed")
            return 1

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_orchestrator_with_gateway())
    sys.exit(exit_code)
