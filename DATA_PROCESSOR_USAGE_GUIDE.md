# Data Processor - Usage Guide via Orchestrator

## Overview

The data processor agent transforms and analyzes structured data (JSON/dict format) through the orchestrator. This guide shows you exactly how to use it.

---

## Table of Contents

1. [How It Gets Invoked](#how-it-gets-invoked)
2. [Quick Start Examples](#quick-start-examples)
3. [Input Formats](#input-formats)
4. [All Operations Explained](#all-operations-explained)
5. [Via Interactive Orchestrator](#via-interactive-orchestrator)
6. [Programmatic Usage](#programmatic-usage)
7. [Real-World Examples](#real-world-examples)
8. [Troubleshooting](#troubleshooting)

---

## How It Gets Invoked

The orchestrator routes queries to the data processor based on these rules (from `config/rules.yaml`):

### Routing Triggers

The data processor is invoked when queries contain:
- **"transform"** - Transform/reshape data
- **"process"** - General processing
- **"convert"** - Convert formats
- **"data"** field exists in input

**Rule Priority**: 80 (lower than math/search, but still high)

### Example Auto-Routing

```python
# These queries automatically route to data_processor:
"transform the employee data"
"process the sales data"
"convert the records to a new format"
{"data": [...], "operation": "aggregate"}  # JSON with data field
```

---

## Quick Start Examples

### Example 1: Simple Transform

```python
from agent_orchestrator import Orchestrator
import asyncio
import json

async def transform_example():
    orchestrator = Orchestrator()
    await orchestrator.initialize()

    # Load sample data
    with open('examples/sample_data.json') as f:
        employees = json.load(f)

    # Transform: Select specific fields
    result = await orchestrator.process({
        "query": "transform employee data selecting name and salary",
        "data": employees,
        "operation": "transform",
        "filters": {"select": ["name", "salary"]}
    })

    if result['success']:
        data = result['data']['data_processor']
        print(f"Transformed {data['input_count']} records")
        print("First 3 results:")
        for record in data['result'][:3]:
            print(f"  {record}")

    await orchestrator.cleanup()

asyncio.run(transform_example())
```

**Output**:
```
Transformed 8 records
First 3 results:
  {'name': 'Alice Johnson', 'salary': 95000}
  {'name': 'Bob Smith', 'salary': 65000}
  {'name': 'Charlie Davis', 'salary': 85000}
```

### Example 2: Filter Data

```python
async def filter_example():
    orchestrator = Orchestrator()
    await orchestrator.initialize()

    with open('examples/sample_data.json') as f:
        employees = json.load(f)

    # Filter: Engineering department only
    result = await orchestrator.process({
        "query": "filter engineering employees",
        "data": employees,
        "operation": "filter",
        "filters": {"conditions": {"department": "Engineering"}}
    })

    if result['success']:
        data = result['data']['data_processor']
        print(f"Found {data['output_count']} engineers:")
        for emp in data['result']:
            print(f"  {emp['name']} - {emp['role']}")

    await orchestrator.cleanup()

asyncio.run(filter_example())
```

**Output**:
```
Found 4 engineers:
  Alice Johnson - Senior Developer
  Bob Smith - Junior Developer
  Eve Williams - DevOps Engineer
  Henry Wilson - Tech Lead
```

### Example 3: Aggregate Statistics

```python
async def aggregate_example():
    orchestrator = Orchestrator()
    await orchestrator.initialize()

    with open('examples/sample_data.json') as f:
        employees = json.load(f)

    # Aggregate: Calculate salary statistics
    result = await orchestrator.process({
        "query": "calculate salary statistics",
        "data": employees,
        "operation": "aggregate",
        "filters": {
            "aggregations": ["count", "avg", "min", "max", "sum"]
        }
    })

    if result['success']:
        data = result['data']['data_processor']
        stats = data['result']
        print(f"Analyzed {data['input_count']} employees:")
        print(f"  Total employees: {stats['count']}")
        print(f"  Average salary: ${stats['salary_avg']:,.2f}")
        print(f"  Min salary: ${stats['salary_min']:,}")
        print(f"  Max salary: ${stats['salary_max']:,}")
        print(f"  Total payroll: ${stats['salary_sum']:,}")

    await orchestrator.cleanup()

asyncio.run(aggregate_example())
```

**Output**:
```
Analyzed 8 employees:
  Total employees: 8
  Average salary: $79,750.00
  Min salary: $55,000
  Max salary: $110,000
  Total payroll: $638,000
```

---

## Input Formats

The data processor accepts input in multiple formats:

### Format 1: Full JSON Request (Recommended)

```python
request = {
    "query": "human-readable description",
    "data": [...],  # Your data (list of dicts or single dict)
    "operation": "transform|filter|aggregate|sort",
    "filters": {...}  # Operation-specific parameters
}

result = await orchestrator.process(request)
```

### Format 2: Minimal (Let Orchestrator Parse)

```python
# Orchestrator will try to infer operation from query
request = {
    "query": "transform employee data",
    "data": [...]
}

result = await orchestrator.process(request)
```

### Format 3: Natural Language (Experimental)

```python
# For simple operations, you can try natural language
# But structured format is more reliable
request = {
    "query": "show me employees in Engineering department",
    "data": employees
}

result = await orchestrator.process(request)
```

---

## All Operations Explained

### 1. Transform Operation

**Purpose**: Select, rename, or reshape fields

**Filters**:
- `select` (list): Fields to include
- `rename` (dict): Field name mappings

**Example 1: Select Fields**
```python
result = await orchestrator.process({
    "data": employees,
    "operation": "transform",
    "filters": {
        "select": ["name", "department", "salary"]
    }
})
```

**Example 2: Rename Fields**
```python
result = await orchestrator.process({
    "data": employees,
    "operation": "transform",
    "filters": {
        "rename": {
            "name": "employee_name",
            "role": "job_title"
        }
    }
})
```

**Example 3: Select and Rename**
```python
result = await orchestrator.process({
    "data": employees,
    "operation": "transform",
    "filters": {
        "select": ["name", "salary", "department"],
        "rename": {"name": "full_name"}
    }
})
```

### 2. Filter Operation

**Purpose**: Filter records by conditions

**Filters**:
- `conditions` (dict): Field-value pairs to match

**Example 1: Single Condition**
```python
result = await orchestrator.process({
    "data": employees,
    "operation": "filter",
    "filters": {
        "conditions": {"department": "Engineering"}
    }
})
```

**Example 2: Multiple Conditions (AND logic)**
```python
result = await orchestrator.process({
    "data": employees,
    "operation": "filter",
    "filters": {
        "conditions": {
            "department": "Engineering",
            "years_of_service": 5
        }
    }
})
# Only matches if ALL conditions are met
```

### 3. Aggregate Operation

**Purpose**: Calculate statistics (count, sum, avg, min, max)

**Filters**:
- `aggregations` (list): Functions to apply
- `group_by` (string, optional): Field to group by

**Available Aggregations**:
- `count` - Count records
- `sum` - Sum numeric fields
- `avg` - Average numeric fields
- `min` - Minimum values
- `max` - Maximum values

**Example 1: Overall Statistics**
```python
result = await orchestrator.process({
    "data": employees,
    "operation": "aggregate",
    "filters": {
        "aggregations": ["count", "avg", "max"]
    }
})

# Result includes:
# {
#   "count": 8,
#   "salary_avg": 79750,
#   "salary_max": 110000,
#   "years_of_service_avg": 4.0,
#   ...
# }
```

**Example 2: Group By Department**
```python
result = await orchestrator.process({
    "data": employees,
    "operation": "aggregate",
    "filters": {
        "group_by": "department",
        "aggregations": ["count", "avg"]
    }
})

# Result includes:
# {
#   "Engineering": {
#     "count": 4,
#     "salary_avg": 90000
#   },
#   "Sales": {
#     "count": 2,
#     "salary_avg": 70000
#   },
#   ...
# }
```

### 4. Sort Operation

**Purpose**: Sort records by field

**Filters**:
- `sort_by` (string): Field to sort by
- `reverse` (bool): Descending order (default: false)

**Example 1: Sort Ascending**
```python
result = await orchestrator.process({
    "data": employees,
    "operation": "sort",
    "filters": {
        "sort_by": "salary"
    }
})
# Lowest salary first
```

**Example 2: Sort Descending**
```python
result = await orchestrator.process({
    "data": employees,
    "operation": "sort",
    "filters": {
        "sort_by": "salary",
        "reverse": True
    }
})
# Highest salary first
```

---

## Via Interactive Orchestrator

You can use the data processor interactively:

```bash
python3 test_orchestrator_interactive.py
```

### Method 1: Paste JSON Data Inline

```python
You > {
  "query": "transform employee data",
  "data": [
    {"name": "Alice", "age": 30, "salary": 95000},
    {"name": "Bob", "age": 25, "salary": 65000}
  ],
  "operation": "aggregate",
  "filters": {"aggregations": ["count", "avg"]}
}
```

### Method 2: Reference Sample File

Since the interactive script doesn't directly support file loading, you'll need to create a wrapper script:

```python
# Create: quick_data_process.py
import asyncio
import json
from agent_orchestrator import Orchestrator

async def process_sample_data():
    orchestrator = Orchestrator()
    await orchestrator.initialize()

    # Load sample data
    with open('examples/sample_data.json') as f:
        data = json.load(f)

    # Process it
    result = await orchestrator.process({
        "query": "calculate department statistics",
        "data": data,
        "operation": "aggregate",
        "filters": {
            "group_by": "department",
            "aggregations": ["count", "avg"]
        }
    })

    print(json.dumps(result, indent=2))

    await orchestrator.cleanup()

asyncio.run(process_sample_data())
```

Run it:
```bash
python3 quick_data_process.py
```

---

## Programmatic Usage

### Complete Example: Multi-Step Analysis

```python
#!/usr/bin/env python3
"""Complete data analysis pipeline using data processor."""

import asyncio
import json
from agent_orchestrator import Orchestrator

async def analyze_employees():
    orchestrator = Orchestrator()
    await orchestrator.initialize()

    # Load data
    with open('examples/sample_data.json') as f:
        employees = json.load(f)

    print("=" * 70)
    print("EMPLOYEE DATA ANALYSIS")
    print("=" * 70)

    # Step 1: Get overview
    print("\n1. OVERVIEW")
    result = await orchestrator.process({
        "data": employees,
        "operation": "aggregate",
        "filters": {"aggregations": ["count"]}
    })
    total = result['data']['data_processor']['result']['count']
    print(f"   Total employees: {total}")

    # Step 2: Department breakdown
    print("\n2. DEPARTMENT BREAKDOWN")
    result = await orchestrator.process({
        "data": employees,
        "operation": "aggregate",
        "filters": {
            "group_by": "department",
            "aggregations": ["count", "avg"]
        }
    })
    for dept, stats in result['data']['data_processor']['result'].items():
        print(f"   {dept}:")
        print(f"     Employees: {stats['count']}")
        print(f"     Avg Salary: ${stats.get('salary_avg', 0):,.2f}")

    # Step 3: Top earners
    print("\n3. TOP 3 EARNERS")
    result = await orchestrator.process({
        "data": employees,
        "operation": "sort",
        "filters": {
            "sort_by": "salary",
            "reverse": True
        }
    })
    for i, emp in enumerate(result['data']['data_processor']['result'][:3], 1):
        print(f"   {i}. {emp['name']}: ${emp['salary']:,} ({emp['role']})")

    # Step 4: Engineering team only
    print("\n4. ENGINEERING TEAM")
    result = await orchestrator.process({
        "data": employees,
        "operation": "filter",
        "filters": {
            "conditions": {"department": "Engineering"}
        }
    })
    engineers = result['data']['data_processor']['result']
    print(f"   Total: {len(engineers)} engineers")
    for emp in engineers:
        print(f"   - {emp['name']} ({emp['role']}, {emp['years_of_service']} years)")

    # Step 5: High performers (rating >= 4.5)
    print("\n5. HIGH PERFORMERS (Rating >= 4.5)")
    high_performers = [e for e in employees if e['performance_rating'] >= 4.5]
    result = await orchestrator.process({
        "data": high_performers,
        "operation": "transform",
        "filters": {
            "select": ["name", "department", "performance_rating"]
        }
    })
    for emp in result['data']['data_processor']['result']:
        print(f"   - {emp['name']} ({emp['department']}): {emp['performance_rating']}")

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)

    await orchestrator.cleanup()

if __name__ == "__main__":
    asyncio.run(analyze_employees())
```

Save as `analyze_employees.py` and run:
```bash
python3 analyze_employees.py
```

---

## Real-World Examples

### Example 1: Sales Data Analysis

```python
sales_data = [
    {"id": 1, "region": "North", "product": "Widget A", "revenue": 15000, "units": 150},
    {"id": 2, "region": "South", "product": "Widget B", "revenue": 22000, "units": 200},
    {"id": 3, "region": "North", "product": "Widget B", "revenue": 18000, "units": 180},
    {"id": 4, "region": "East", "product": "Widget A", "revenue": 12000, "units": 120},
]

# Group by region
result = await orchestrator.process({
    "data": sales_data,
    "operation": "aggregate",
    "filters": {
        "group_by": "region",
        "aggregations": ["count", "sum", "avg"]
    }
})

# Result:
# {
#   "North": {"count": 2, "revenue_sum": 33000, "units_sum": 330, ...},
#   "South": {"count": 1, "revenue_sum": 22000, "units_sum": 200, ...},
#   ...
# }
```

### Example 2: Customer Segmentation

```python
customers = [
    {"id": 1, "name": "Alice", "segment": "Premium", "lifetime_value": 5000},
    {"id": 2, "name": "Bob", "segment": "Standard", "lifetime_value": 1200},
    {"id": 3, "name": "Charlie", "segment": "Premium", "lifetime_value": 7500},
]

# Filter premium customers
result = await orchestrator.process({
    "data": customers,
    "operation": "filter",
    "filters": {
        "conditions": {"segment": "Premium"}
    }
})

# Then aggregate
premium_customers = result['data']['data_processor']['result']
result = await orchestrator.process({
    "data": premium_customers,
    "operation": "aggregate",
    "filters": {
        "aggregations": ["count", "avg", "sum"]
    }
})

print(f"Premium customers: {result['data']['data_processor']['result']['count']}")
print(f"Avg LTV: ${result['data']['data_processor']['result']['lifetime_value_avg']:,.2f}")
```

### Example 3: Data Cleanup Pipeline

```python
# Step 1: Select relevant fields
result = await orchestrator.process({
    "data": raw_data,
    "operation": "transform",
    "filters": {
        "select": ["id", "name", "email", "status"]
    }
})

cleaned_data = result['data']['data_processor']['result']

# Step 2: Filter active records
result = await orchestrator.process({
    "data": cleaned_data,
    "operation": "filter",
    "filters": {
        "conditions": {"status": "active"}
    }
})

active_data = result['data']['data_processor']['result']

# Step 3: Sort by name
result = await orchestrator.process({
    "data": active_data,
    "operation": "sort",
    "filters": {
        "sort_by": "name"
    }
})

final_data = result['data']['data_processor']['result']
```

---

## Troubleshooting

### Issue 1: Agent Not Invoked

**Problem**: Query doesn't route to data processor

**Solution**: Include routing keywords or specify explicitly

```python
# Bad (might not route correctly)
result = await orchestrator.process({
    "data": employees
})

# Good (clear routing)
result = await orchestrator.process({
    "query": "process employee data",  # Include "process" keyword
    "data": employees,
    "operation": "aggregate"
})

# Best (explicit agent call)
data_processor = orchestrator.agent_registry.get("data_processor")
result = await data_processor.call({
    "data": employees,
    "operation": "aggregate",
    "filters": {"aggregations": ["count"]}
})
```

### Issue 2: Validation Errors

**Problem**: Output doesn't match schema

**Check the logs**:
```bash
cat logs/queries/query_*.json | jq '.validation.validation_details'
```

**Common issues**:
- Missing required fields in result
- Wrong data types
- Invalid operation name

**Solution**: Ensure operation is valid:
```python
# Valid operations
operations = ["transform", "filter", "aggregate", "sort"]

# Invalid
"operation": "group_by"  # ❌ Should be "aggregate" with group_by filter
```

### Issue 3: Empty Results

**Problem**: No results returned

**Debug**:
```python
result = await orchestrator.process({
    "data": employees,
    "operation": "filter",
    "filters": {"conditions": {"department": "Engineering"}}
})

data = result['data']['data_processor']
print(f"Input: {data['input_count']} records")
print(f"Output: {data['output_count']} records")
print(f"Filters: {data['filters_applied']}")

if data['output_count'] == 0:
    print("No records matched filter conditions")
    print("Check that field names and values are exact matches")
```

### Issue 4: Performance with Large Datasets

**Problem**: Slow processing

**Solutions**:

1. **Limit data size**:
```python
# Process first 1000 records
result = await orchestrator.process({
    "data": large_dataset[:1000],
    "operation": "aggregate"
})
```

2. **Use aggregation instead of returning all records**:
```python
# Better: Return aggregated stats
result = await orchestrator.process({
    "data": large_dataset,
    "operation": "aggregate",
    "filters": {"aggregations": ["count", "avg"]}
})

# Instead of: Returning all records
result = await orchestrator.process({
    "data": large_dataset,
    "operation": "sort"
})  # Returns all records sorted
```

---

## Best Practices

### 1. Always Provide Operation

```python
# Good
result = await orchestrator.process({
    "data": data,
    "operation": "aggregate",  # Explicit
    "filters": {...}
})

# Risky (might not work)
result = await orchestrator.process({
    "data": data,
    "filters": {...}
})
```

### 2. Use Appropriate Operations

```python
# For counting/stats: use aggregate
operation = "aggregate"

# For selecting fields: use transform
operation = "transform"

# For filtering: use filter
operation = "filter"

# For ordering: use sort
operation = "sort"
```

### 3. Chain Operations

```python
# Step 1: Filter
result1 = await orchestrator.process({
    "data": all_employees,
    "operation": "filter",
    "filters": {"conditions": {"department": "Engineering"}}
})

engineers = result1['data']['data_processor']['result']

# Step 2: Sort filtered results
result2 = await orchestrator.process({
    "data": engineers,
    "operation": "sort",
    "filters": {"sort_by": "salary", "reverse": True}
})

top_paid_engineers = result2['data']['data_processor']['result']
```

### 4. Handle Errors Gracefully

```python
result = await orchestrator.process({
    "data": employees,
    "operation": "aggregate",
    "filters": {"aggregations": ["count", "avg"]}
})

if not result['success']:
    print(f"Error: {result.get('error')}")
    # Handle error
else:
    data = result['data'].get('data_processor')
    if data:
        print(f"Processed {data['input_count']} records")
    else:
        print("No data processor output found")
```

---

## Summary

### Quick Reference

```python
# Transform: Select/rename fields
{"operation": "transform", "filters": {"select": ["field1", "field2"]}}

# Filter: Match conditions
{"operation": "filter", "filters": {"conditions": {"field": "value"}}}

# Aggregate: Calculate stats
{"operation": "aggregate", "filters": {"aggregations": ["count", "avg"]}}

# Sort: Order by field
{"operation": "sort", "filters": {"sort_by": "field", "reverse": True}}
```

### Key Points

1. ✅ Always include `"data"` field with your dataset
2. ✅ Specify `"operation"` explicitly
3. ✅ Use `"filters"` for operation-specific parameters
4. ✅ Check `result['success']` before accessing data
5. ✅ Access output via `result['data']['data_processor']`

---

**Ready to process data!** 🚀

For more examples, see:
- `examples/test_data_processor.py` - Complete test suite
- `examples/sample_data.json` - Sample dataset
- `SCHEMAS_AND_VALIDATION.md` - Full documentation
