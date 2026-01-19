# Using Data Processor in Interactive Orchestrator

## Quick Start

1. **Start the interactive orchestrator:**
   ```bash
   python3 test_orchestrator_interactive.py
   ```

2. **Load sample data:**
   ```
   You > /load-sample-data
   ```

   This will show you:
   - Preview of 8 employee records
   - 3 ready-to-use example queries
   - Just copy and paste!

3. **Run a query:**
   Copy one of the generated examples and paste it at the prompt.

---

## The Problem You Encountered

**What you tried:**
```json
{
  "query": "transform employee data",
  "data": [...],
  "operation": "aggregate",
  "filters": {"aggregations": ["count", "avg"]}
}
```

**Why it failed:**
- The `...` is not valid JSON (it's a placeholder)
- You need to provide actual employee data as an array of objects

---

## Working Examples

### Example 1: Aggregate (Count and Average)

**Complete working query:**
```json
{"query": "aggregate employee data", "data": [{"name": "Alice", "age": 30, "salary": 95000}, {"name": "Bob", "age": 25, "salary": 65000}], "operation": "aggregate", "filters": {"aggregations": ["count", "avg"]}}
```

**Expected output:**
```
✅ SUCCESS
Agents Used: data_processor

Data Processor:
  Operation: aggregate
  Input: 2 records
  Output: 1 result
  Result: {
    "count": 2,
    "age_avg": 27.5,
    "salary_avg": 80000.0
  }
```

### Example 2: Filter (by Department)

**Complete working query:**
```json
{"query": "filter engineering employees", "data": [{"name": "Alice", "dept": "Engineering", "salary": 95000}, {"name": "Bob", "dept": "Sales", "salary": 65000}, {"name": "Charlie", "dept": "Engineering", "salary": 110000}], "operation": "filter", "filters": {"conditions": {"dept": "Engineering"}}}
```

**Expected output:**
```
✅ SUCCESS
Data Processor:
  Operation: filter
  Input: 3 records
  Output: 2 records (Alice and Charlie)
```

### Example 3: Sort (by Salary)

**Complete working query:**
```json
{"query": "sort by salary", "data": [{"name": "Alice", "salary": 95000}, {"name": "Bob", "salary": 65000}, {"name": "Charlie", "salary": 110000}], "operation": "sort", "filters": {"sort_by": "salary", "reverse": true}}
```

**Expected output:**
```
✅ SUCCESS
Data Processor:
  Operation: sort
  Output: [Charlie (110k), Alice (95k), Bob (65k)]
```

---

## Using the `/load-sample-data` Command

This is the **easiest way** to test the data processor!

### Step 1: Load sample data

```
You > /load-sample-data
```

### Step 2: Output will show

```
✅ Loaded 8 employee records from examples/sample_data.json

Sample Data Preview:
[
  {
    "id": "emp001",
    "name": "Alice Johnson",
    "department": "Engineering",
    "role": "Senior Developer",
    "salary": 95000,
    "years_of_service": 5,
    "performance_rating": 4.5
  },
  {
    "id": "emp002",
    "name": "Bob Smith",
    ...
  }
]

Example Queries:

1. Aggregate (count and average):
{"query": "aggregate employee data", "data": [...full data here...], "operation": "aggregate", "filters": {"aggregations": ["count", "avg"]}}

2. Filter (Engineering department):
{"query": "filter engineering employees", "data": [...full data here...], "operation": "filter", "filters": {"conditions": {"department": "Engineering"}}}

3. Sort (by salary descending):
{"query": "sort by salary", "data": [...full data here...], "operation": "sort", "filters": {"sort_by": "salary", "reverse": true}}

💡 Copy one of the examples above and paste it as your query!
```

### Step 3: Copy and paste

Just copy one of the complete JSON examples and paste it at the prompt!

---

## Data Format Requirements

The `data` field must contain:
- **Valid JSON array** of objects
- Each object should have consistent fields
- No placeholders like `...`

### ✅ Valid Data
```json
"data": [
  {"name": "Alice", "age": 30},
  {"name": "Bob", "age": 25}
]
```

### ❌ Invalid Data
```json
"data": [...]  // Not valid JSON!
"data": "..."  // Not an array!
```

---

## All Data Processor Operations

### 1. **Transform** - Select/Rename Fields

```json
{
  "query": "transform data",
  "data": [{"name": "Alice", "age": 30, "salary": 95000}],
  "operation": "transform",
  "filters": {
    "select": ["name", "salary"]
  }
}
```

Result: `[{"name": "Alice", "salary": 95000}]`

### 2. **Filter** - Filter by Conditions

```json
{
  "query": "filter data",
  "data": [{"name": "Alice", "salary": 95000}, {"name": "Bob", "salary": 65000}],
  "operation": "filter",
  "filters": {
    "conditions": {"salary": 95000}
  }
}
```

Result: Only records where salary = 95000

### 3. **Aggregate** - Calculate Statistics

```json
{
  "query": "aggregate data",
  "data": [{"salary": 95000}, {"salary": 65000}],
  "operation": "aggregate",
  "filters": {
    "aggregations": ["count", "avg", "min", "max", "sum"]
  }
}
```

Result: Statistics for all numeric fields

### 4. **Sort** - Sort by Field

```json
{
  "query": "sort data",
  "data": [{"name": "Alice", "salary": 95000}, {"name": "Bob", "salary": 65000}],
  "operation": "sort",
  "filters": {
    "sort_by": "salary",
    "reverse": true
  }
}
```

Result: Records sorted by salary (highest first)

---

## Troubleshooting

### Error: "process_data() missing 1 required positional argument: 'data'"

**Cause:** The `data` field is missing or invalid

**Fix:** Ensure you have a valid JSON array in the `data` field:
```json
"data": [{"name": "Alice", "age": 30}]  // ✅ Good
"data": [...]  // ❌ Bad - not valid JSON
```

### Error: "JSONDecodeError: Expecting value"

**Cause:** Invalid JSON syntax (often from using `...` as a placeholder)

**Fix:** Use the `/load-sample-data` command to get complete, valid examples

### AI Validation Rejecting Selection

**Cause:** Query keywords trigger wrong rule (rare after recent fixes)

**Fix:** Be more specific in the query:
- Use "aggregate employee data" instead of just "aggregate"
- Include "data processor" in your query
- Make sure the `data` field is present

---

## Tips for Success

1. **Use `/load-sample-data` first** - This is the easiest way to get started
2. **Copy complete examples** - Don't try to type JSON manually
3. **Test with small data first** - Use 2-3 records to verify it works
4. **Check AI validation logs** - See if the right agent was selected
5. **Use `/examples`** - Shows other query examples for different agents

---

## Summary

**DO:**
- ✅ Use `/load-sample-data` for ready-made examples
- ✅ Provide actual JSON arrays, not placeholders
- ✅ Copy and paste complete examples
- ✅ Test with the provided sample data

**DON'T:**
- ❌ Use `...` as a placeholder in JSON
- ❌ Type complex JSON manually (use copy/paste)
- ❌ Skip the `data` field
- ❌ Use invalid JSON syntax

---

**Quick Test:**
```bash
# Start interactive mode
python3 test_orchestrator_interactive.py

# At the prompt
You > /load-sample-data

# Copy one of the examples shown and paste it
# Should work immediately!
```

---

**Created:** January 19, 2026
**Updated:** January 19, 2026
**Status:** ✅ Ready to use
