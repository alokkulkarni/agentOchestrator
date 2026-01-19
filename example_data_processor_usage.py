#!/usr/bin/env python3
"""
Simple example showing how to use data processor through orchestrator.

This script demonstrates all 4 operations with the sample employee data.

Usage:
    python3 example_data_processor_usage.py
"""

import asyncio
import json
from dotenv import load_dotenv
from agent_orchestrator import Orchestrator

# Load environment variables
load_dotenv()


async def main():
    print("=" * 70)
    print("DATA PROCESSOR VIA ORCHESTRATOR - EXAMPLES")
    print("=" * 70)

    # Initialize orchestrator
    orchestrator = Orchestrator()
    await orchestrator.initialize()

    # Load sample data
    with open('examples/sample_data.json') as f:
        employees = json.load(f)

    print(f"\nLoaded {len(employees)} employee records")

    # ========================================================================
    # Example 1: TRANSFORM - Select specific fields
    # ========================================================================
    print("\n" + "-" * 70)
    print("EXAMPLE 1: Transform - Select Fields")
    print("-" * 70)

    result = await orchestrator.process({
        "query": "transform employee data",
        "data": employees,
        "operation": "transform",
        "filters": {
            "select": ["name", "department", "salary"]
        }
    })

    if result['success']:
        data = result['data']['data_processor']
        print(f"✅ Transformed {data['input_count']} → {data['output_count']} records")
        print("\nFirst 3 results:")
        for i, record in enumerate(data['result'][:3], 1):
            print(f"  {i}. {record}")
    else:
        print(f"❌ Error: {result.get('error')}")

    # ========================================================================
    # Example 2: FILTER - Engineering department only
    # ========================================================================
    print("\n" + "-" * 70)
    print("EXAMPLE 2: Filter - Engineering Department")
    print("-" * 70)

    result = await orchestrator.process({
        "query": "filter engineering employees",
        "data": employees,
        "operation": "filter",
        "filters": {
            "conditions": {"department": "Engineering"}
        }
    })

    if result['success']:
        data = result['data']['data_processor']
        print(f"✅ Filtered {data['input_count']} → {data['output_count']} records")
        print("\nEngineering employees:")
        for i, emp in enumerate(data['result'], 1):
            print(f"  {i}. {emp['name']} - {emp['role']} (${emp['salary']:,})")
    else:
        print(f"❌ Error: {result.get('error')}")

    # ========================================================================
    # Example 3: AGGREGATE - Calculate salary statistics
    # ========================================================================
    print("\n" + "-" * 70)
    print("EXAMPLE 3: Aggregate - Salary Statistics")
    print("-" * 70)

    result = await orchestrator.process({
        "query": "calculate employee statistics",
        "data": employees,
        "operation": "aggregate",
        "filters": {
            "aggregations": ["count", "avg", "min", "max", "sum"]
        }
    })

    if result['success']:
        data = result['data']['data_processor']
        stats = data['result']
        print(f"✅ Analyzed {data['input_count']} employees\n")
        print("Salary Statistics:")
        print(f"  Total employees: {stats['count']}")
        print(f"  Average salary: ${stats['salary_avg']:,.2f}")
        print(f"  Min salary: ${stats['salary_min']:,}")
        print(f"  Max salary: ${stats['salary_max']:,}")
        print(f"  Total payroll: ${stats['salary_sum']:,}")
    else:
        print(f"❌ Error: {result.get('error')}")

    # ========================================================================
    # Example 4: AGGREGATE - Group by department
    # ========================================================================
    print("\n" + "-" * 70)
    print("EXAMPLE 4: Aggregate - Group by Department")
    print("-" * 70)

    result = await orchestrator.process({
        "query": "group employees by department",
        "data": employees,
        "operation": "aggregate",
        "filters": {
            "group_by": "department",
            "aggregations": ["count", "avg"]
        }
    })

    if result['success']:
        data = result['data']['data_processor']
        print(f"✅ Grouped {data['input_count']} employees by department\n")
        print("Department Statistics:")
        for dept, stats in data['result'].items():
            print(f"\n  {dept}:")
            print(f"    Employees: {stats['count']}")
            print(f"    Avg Salary: ${stats.get('salary_avg', 0):,.2f}")
            print(f"    Avg Experience: {stats.get('years_of_service_avg', 0):.1f} years")
    else:
        print(f"❌ Error: {result.get('error')}")

    # ========================================================================
    # Example 5: SORT - Top 5 earners
    # ========================================================================
    print("\n" + "-" * 70)
    print("EXAMPLE 5: Sort - Top Earners")
    print("-" * 70)

    result = await orchestrator.process({
        "query": "sort employees by salary",
        "data": employees,
        "operation": "sort",
        "filters": {
            "sort_by": "salary",
            "reverse": True  # Highest first
        }
    })

    if result['success']:
        data = result['data']['data_processor']
        print(f"✅ Sorted {data['output_count']} employees by salary\n")
        print("Top 5 Earners:")
        for i, emp in enumerate(data['result'][:5], 1):
            print(f"  {i}. {emp['name']}: ${emp['salary']:,}")
            print(f"     {emp['role']} - {emp['department']}")
    else:
        print(f"❌ Error: {result.get('error')}")

    # ========================================================================
    # Example 6: CHAINING - Filter then Sort
    # ========================================================================
    print("\n" + "-" * 70)
    print("EXAMPLE 6: Chaining Operations - Filter + Sort")
    print("-" * 70)

    # Step 1: Filter Engineering employees
    result1 = await orchestrator.process({
        "query": "filter engineering employees",
        "data": employees,
        "operation": "filter",
        "filters": {"conditions": {"department": "Engineering"}}
    })

    if result1['success']:
        engineers = result1['data']['data_processor']['result']
        print(f"✅ Step 1: Filtered to {len(engineers)} engineers")

        # Step 2: Sort by salary
        result2 = await orchestrator.process({
            "query": "sort engineers by salary",
            "data": engineers,
            "operation": "sort",
            "filters": {"sort_by": "salary", "reverse": True}
        })

        if result2['success']:
            sorted_engineers = result2['data']['data_processor']['result']
            print(f"✅ Step 2: Sorted {len(sorted_engineers)} engineers\n")
            print("Top Engineering Earners:")
            for i, emp in enumerate(sorted_engineers, 1):
                print(f"  {i}. {emp['name']}: ${emp['salary']:,} ({emp['role']})")
        else:
            print(f"❌ Step 2 failed: {result2.get('error')}")
    else:
        print(f"❌ Step 1 failed: {result1.get('error')}")

    # Cleanup
    await orchestrator.cleanup()

    print("\n" + "=" * 70)
    print("✅ ALL EXAMPLES COMPLETED")
    print("=" * 70)
    print("\nFor more details, see:")
    print("  - DATA_PROCESSOR_USAGE_GUIDE.md")
    print("  - examples/test_data_processor.py")
    print("  - SCHEMAS_AND_VALIDATION.md")


if __name__ == "__main__":
    asyncio.run(main())
