#!/usr/bin/env python3
"""
Test script for Data Processor Agent

Demonstrates various data processing operations:
- Transform (select, rename fields)
- Filter (by conditions)
- Aggregate (statistics, group by)
- Sort (by field)

Usage:
    python3 examples/test_data_processor.py
"""

import json
from pathlib import Path

from sample_data_processor import process_data

# Load sample data
data_file = Path(__file__).parent / "sample_data.json"
with open(data_file) as f:
    sample_data = json.load(f)

print("=" * 70)
print("DATA PROCESSOR AGENT - TEST EXAMPLES")
print("=" * 70)

print(f"\nLoaded {len(sample_data)} employee records")
print("\n" + "-" * 70)

# Example 1: Transform - Select specific fields
print("\nEXAMPLE 1: Transform - Select Fields")
print("-" * 70)
print("Operation: Select only 'name', 'department', and 'salary' fields")

result1 = process_data(
    data=sample_data,
    operation="transform",
    filters={"select": ["name", "department", "salary"]}
)

print(f"\nInput: {result1['input_count']} records")
print(f"Output: {result1['output_count']} records")
print("\nFirst 3 results:")
for i, record in enumerate(result1['result'][:3], 1):
    print(f"  {i}. {record}")

# Example 2: Transform - Rename fields
print("\n" + "-" * 70)
print("\nEXAMPLE 2: Transform - Rename Fields")
print("-" * 70)
print("Operation: Rename 'name' → 'employee_name', 'role' → 'position'")

result2 = process_data(
    data=sample_data,
    operation="transform",
    filters={"rename": {"name": "employee_name", "role": "position"}}
)

print(f"\nInput: {result2['input_count']} records")
print(f"Output: {result2['output_count']} records")
print("\nFirst 2 results:")
for i, record in enumerate(result2['result'][:2], 1):
    print(f"  {i}. {json.dumps(record, indent=4)}")

# Example 3: Filter - Find employees by department
print("\n" + "-" * 70)
print("\nEXAMPLE 3: Filter - By Department")
print("-" * 70)
print("Operation: Filter employees in 'Engineering' department")

result3 = process_data(
    data=sample_data,
    operation="filter",
    filters={"conditions": {"department": "Engineering"}}
)

print(f"\nInput: {result3['input_count']} records")
print(f"Output: {result3['output_count']} records (filtered)")
print("\nFiltered employees:")
for i, record in enumerate(result3['result'], 1):
    print(f"  {i}. {record['name']} - {record['role']} (${record['salary']:,})")

# Example 4: Aggregate - Calculate statistics
print("\n" + "-" * 70)
print("\nEXAMPLE 4: Aggregate - Overall Statistics")
print("-" * 70)
print("Operation: Calculate count, avg, min, max for all numeric fields")

result4 = process_data(
    data=sample_data,
    operation="aggregate",
    filters={"aggregations": ["count", "avg", "min", "max"]}
)

print(f"\nInput: {result4['input_count']} records")
print("\nAggregated Statistics:")
for key, value in result4['result'].items():
    if isinstance(value, float):
        print(f"  {key}: {value:.2f}")
    else:
        print(f"  {key}: {value}")

# Example 5: Aggregate - Group by department
print("\n" + "-" * 70)
print("\nEXAMPLE 5: Aggregate - Group By Department")
print("-" * 70)
print("Operation: Calculate statistics grouped by department")

result5 = process_data(
    data=sample_data,
    operation="aggregate",
    filters={
        "group_by": "department",
        "aggregations": ["count", "avg", "sum"]
    }
)

print(f"\nInput: {result5['input_count']} records")
print("\nDepartment Statistics:")
for dept, stats in result5['result'].items():
    print(f"\n  {dept}:")
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"    {key}: {value:.2f}")
        else:
            print(f"    {key}: {value}")

# Example 6: Sort - By salary (descending)
print("\n" + "-" * 70)
print("\nEXAMPLE 6: Sort - By Salary (Highest First)")
print("-" * 70)
print("Operation: Sort employees by salary in descending order")

result6 = process_data(
    data=sample_data,
    operation="sort",
    filters={"sort_by": "salary", "reverse": True}
)

print(f"\nInput: {result6['input_count']} records")
print(f"Output: {result6['output_count']} records (sorted)")
print("\nTop 5 earners:")
for i, record in enumerate(result6['result'][:5], 1):
    print(f"  {i}. {record['name']}: ${record['salary']:,} ({record['role']})")

# Example 7: Sort - By years of service
print("\n" + "-" * 70)
print("\nEXAMPLE 7: Sort - By Years of Service")
print("-" * 70)
print("Operation: Sort employees by years_of_service (descending)")

result7 = process_data(
    data=sample_data,
    operation="sort",
    filters={"sort_by": "years_of_service", "reverse": True}
)

print(f"\nInput: {result7['input_count']} records")
print("\nMost experienced employees:")
for i, record in enumerate(result7['result'][:5], 1):
    print(f"  {i}. {record['name']}: {record['years_of_service']} years ({record['department']})")

print("\n" + "=" * 70)
print("All examples completed successfully!")
print("=" * 70)

# Example orchestrator queries
print("\n" + "-" * 70)
print("EXAMPLE ORCHESTRATOR QUERIES:")
print("-" * 70)
print("""
To use the data processor through the orchestrator:

1. Transform:
   Query: "process the employee data and select only name and salary fields"

2. Filter:
   Query: "filter employees in the Engineering department"

3. Aggregate:
   Query: "calculate average salary and statistics for all employees"

4. Sort:
   Query: "sort employees by salary in descending order"

5. Group by:
   Query: "group employees by department and calculate statistics"
""")
