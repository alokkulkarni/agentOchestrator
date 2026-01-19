#!/usr/bin/env python3
"""
Quick test to verify data processor routing fix.
"""

import asyncio
import json
from dotenv import load_dotenv
from agent_orchestrator import Orchestrator

load_dotenv()


async def main():
    print("=" * 70)
    print("DATA PROCESSOR ROUTING TEST")
    print("=" * 70)

    # Initialize orchestrator
    orchestrator = Orchestrator()
    await orchestrator.initialize()

    # Test data
    test_data = [
        {"name": "Alice", "age": 30, "salary": 95000},
        {"name": "Bob", "age": 25, "salary": 65000}
    ]

    # Test 1: Aggregate operation (should ONLY route to data_processor)
    print("\n" + "-" * 70)
    print("TEST 1: Aggregate with 'transform employee data' query")
    print("-" * 70)

    result = await orchestrator.process({
        "query": "transform employee data",
        "data": test_data,
        "operation": "aggregate",
        "filters": {"aggregations": ["count", "avg"]}
    })

    if result['success']:
        print("✅ Success!")
        print(f"Agents called: {list(result['data'].keys())}")

        if 'data_processor' in result['data']:
            dp_result = result['data']['data_processor']
            print(f"\nData Processor Result:")
            print(f"  Operation: {dp_result.get('operation')}")
            print(f"  Input count: {dp_result.get('input_count')}")
            print(f"  Statistics: {dp_result.get('result')}")

        if 'calculator' in result['data']:
            print("\n⚠️  WARNING: Calculator was also invoked (should NOT happen!)")
    else:
        print(f"❌ Failed: {result.get('error')}")

    # Test 2: Filter operation
    print("\n" + "-" * 70)
    print("TEST 2: Filter with 'data' field present")
    print("-" * 70)

    result = await orchestrator.process({
        "query": "filter high earners",
        "data": test_data,
        "operation": "filter",
        "filters": {"conditions": {"salary": {"$gte": 80000}}}
    })

    if result['success']:
        print("✅ Success!")
        print(f"Agents called: {list(result['data'].keys())}")

        if 'data_processor' in result['data']:
            dp_result = result['data']['data_processor']
            print(f"\nData Processor Result:")
            print(f"  Operation: {dp_result.get('operation')}")
            print(f"  Found: {dp_result.get('output_count')} records")
    else:
        print(f"❌ Failed: {result.get('error')}")

    # Cleanup
    await orchestrator.cleanup()

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
