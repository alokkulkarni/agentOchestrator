#!/usr/bin/env python3
"""
Quick test of the interactive script to verify it initializes correctly.
"""

import asyncio
import sys

from agent_orchestrator import Orchestrator


async def test_initialization():
    """Test that the orchestrator can be initialized."""
    print("Testing orchestrator initialization...")

    orchestrator = None
    try:
        # Initialize orchestrator
        orchestrator = Orchestrator(config_path="config/orchestrator.yaml")
        await orchestrator.initialize()

        # Get stats
        stats = orchestrator.get_stats()

        print(f"✅ Orchestrator initialized successfully!")
        print(f"   Name: {stats['name']}")
        print(f"   Agents: {stats['agents']['total_agents']}")
        print(f"   Capabilities: {', '.join(stats['agents']['capabilities'])}")

        # Test a simple query
        print("\nTesting a simple query: 'calculate 2 + 2'")
        result = await orchestrator.process({
            "query": "calculate 2 + 2",
            "operation": "add",
            "operands": [2, 2]
        })

        print(f"   Success: {result['success']}")
        if result['success']:
            print(f"   Result: {result['data']['calculator']['result']}")
            print(f"   Agent: {result['_metadata']['agent_trail'][0]}")

        print("\n✅ Interactive script is ready to use!")
        print("\nRun: python3 test_orchestrator_interactive.py")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if orchestrator:
            await orchestrator.cleanup()


if __name__ == "__main__":
    success = asyncio.run(test_initialization())
    sys.exit(0 if success else 1)
