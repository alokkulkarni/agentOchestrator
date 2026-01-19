#!/usr/bin/env python3
"""
Simplest way to use data processor through orchestrator.

This shows the DIRECT approach - calling the agent explicitly.
This is the recommended way for programmatic usage.

Usage:
    python3 simple_data_processor_example.py
"""

import asyncio
import json
from dotenv import load_dotenv
from agent_orchestrator import Orchestrator

# Load environment variables
load_dotenv()


async def main():
    print("=" * 70)
    print("DATA PROCESSOR - DIRECT USAGE (RECOMMENDED)")
    print("=" * 70)

    # Initialize orchestrator
    orchestrator = Orchestrator()
    await orchestrator.initialize()

    # Get the data processor agent directly
    data_processor = orchestrator.agent_registry.get("data_processor")

    if not data_processor:
        print("❌ Data processor agent not found!")
        await orchestrator.cleanup()
        return

    # Load sample data
    with open('examples/sample_data.json') as f:
        employees = json.load(f)

    print(f"\nLoaded {len(employees)} employee records\n")

    # ========================================================================
    # Example 1: Transform - Select Fields
    # ========================================================================
    print("-" * 70)
    print("EXAMPLE 1: Transform - Select Specific Fields")
    print("-" * 70)

    result = await data_processor.call({
        "data": employees,
        "operation": "transform",
        "filters": {
            "select": ["name", "department", "salary"]
        }
    })

    if result.success:
        print(f"✅ Success! Transformed {result.data['input_count']} records\n")
        print("First 3 results:")
        for i, record in enumerate(result.data['result'][:3], 1):
            print(f"  {i}. {record}")
    else:
        print(f"❌ Error: {result.error}")

    # ========================================================================
    # Example 2: Filter - Engineering Only
    # ========================================================================
    print("\n" + "-" * 70)
    print("EXAMPLE 2: Filter - Engineering Department")
    print("-" * 70)

    result = await data_processor.call({
        "data": employees,
        "operation": "filter",
        "filters": {
            "conditions": {"department": "Engineering"}
        }
    })

    if result.success:
        print(f"✅ Success! Found {result.data['output_count']} engineers\n")
        for i, emp in enumerate(result.data['result'], 1):
            print(f"  {i}. {emp['name']} - {emp['role']} (${emp['salary']:,})")
    else:
        print(f"❌ Error: {result.error}")

    # ========================================================================
    # Example 3: Aggregate - Overall Statistics
    # ========================================================================
    print("\n" + "-" * 70)
    print("EXAMPLE 3: Aggregate - Salary Statistics")
    print("-" * 70)

    result = await data_processor.call({
        "data": employees,
        "operation": "aggregate",
        "filters": {
            "aggregations": ["count", "avg", "min", "max", "sum"]
        }
    })

    if result.success:
        stats = result.data['result']
        print(f"✅ Success! Analyzed {result.data['input_count']} employees\n")
        print("Salary Statistics:")
        print(f"  Total employees: {stats['count']}")
        print(f"  Average salary: ${stats['salary_avg']:,.2f}")
        print(f"  Min salary: ${stats['salary_min']:,}")
        print(f"  Max salary: ${stats['salary_max']:,}")
        print(f"  Total payroll: ${stats['salary_sum']:,}")
    else:
        print(f"❌ Error: {result.error}")

    # ========================================================================
    # Example 4: Aggregate - Group by Department
    # ========================================================================
    print("\n" + "-" * 70)
    print("EXAMPLE 4: Aggregate - Group by Department")
    print("-" * 70)

    result = await data_processor.call({
        "data": employees,
        "operation": "aggregate",
        "filters": {
            "group_by": "department",
            "aggregations": ["count", "avg"]
        }
    })

    if result.success:
        print(f"✅ Success! Grouped {result.data['input_count']} employees\n")
        print("Department Statistics:")
        for dept, stats in result.data['result'].items():
            print(f"\n  {dept}:")
            print(f"    Employees: {stats['count']}")
            print(f"    Avg Salary: ${stats.get('salary_avg', 0):,.2f}")
            print(f"    Avg Years: {stats.get('years_of_service_avg', 0):.1f}")
    else:
        print(f"❌ Error: {result.error}")

    # ========================================================================
    # Example 5: Sort - Top Earners
    # ========================================================================
    print("\n" + "-" * 70)
    print("EXAMPLE 5: Sort - Top Earners")
    print("-" * 70)

    result = await data_processor.call({
        "data": employees,
        "operation": "sort",
        "filters": {
            "sort_by": "salary",
            "reverse": True
        }
    })

    if result.success:
        print(f"✅ Success! Sorted {result.data['output_count']} employees\n")
        print("Top 5 Earners:")
        for i, emp in enumerate(result.data['result'][:5], 1):
            print(f"  {i}. {emp['name']}: ${emp['salary']:,}")
            print(f"     {emp['role']} - {emp['department']}")
    else:
        print(f"❌ Error: {result.error}")

    # ========================================================================
    # Example 6: Chaining Operations
    # ========================================================================
    print("\n" + "-" * 70)
    print("EXAMPLE 6: Chain Operations - Filter → Sort")
    print("-" * 70)

    # Step 1: Filter Engineering
    result1 = await data_processor.call({
        "data": employees,
        "operation": "filter",
        "filters": {"conditions": {"department": "Engineering"}}
    })

    if result1.success:
        engineers = result1.data['result']
        print(f"✅ Step 1: Filtered to {len(engineers)} engineers")

        # Step 2: Sort by salary
        result2 = await data_processor.call({
            "data": engineers,
            "operation": "sort",
            "filters": {"sort_by": "salary", "reverse": True}
        })

        if result2.success:
            print(f"✅ Step 2: Sorted {len(result2.data['result'])} engineers\n")
            print("Top Engineering Earners:")
            for i, emp in enumerate(result2.data['result'], 1):
                print(f"  {i}. {emp['name']}: ${emp['salary']:,} ({emp['role']})")
        else:
            print(f"❌ Step 2 failed: {result2.error}")
    else:
        print(f"❌ Step 1 failed: {result1.error}")

    # Cleanup
    await orchestrator.cleanup()

    print("\n" + "=" * 70)
    print("✅ ALL EXAMPLES COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("  1. Get agent: orchestrator.agent_registry.get('data_processor')")
    print("  2. Call directly: agent.call({data, operation, filters})")
    print("  3. Access result: result.data['result']")
    print("\nFor full documentation:")
    print("  - DATA_PROCESSOR_USAGE_GUIDE.md")
    print("  - examples/test_data_processor.py")


if __name__ == "__main__":
    asyncio.run(main())
