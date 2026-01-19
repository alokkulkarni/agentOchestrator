# Quick Data Processor Demo

## Problem: Terminal Can't Handle Long JSON Paste

You encountered this issue:
```
❌ Terminal truncates long JSON when pasting
❌ Can't paste the full employee data array
```

## Solution: One-Command Shortcuts! ✅

No more copy/paste needed! Just type short commands.

---

## How to Use (3 Simple Steps)

### Step 1: Start Interactive Mode

```bash
python3 test_orchestrator_interactive.py
```

### Step 2: View Available Commands

```
You > /load-sample-data
```

**Output:**
```
✅ Loaded 8 employee records from examples/sample_data.json

Sample Data Preview:
[
  {
    "id": "emp001",
    "name": "Alice Johnson",
    "department": "Engineering",
    ...
  }
]

Quick Commands (no copy/paste needed):
  /dp-aggregate - Calculate count, avg, min, max, sum
  /dp-filter    - Filter Engineering department
  /dp-sort      - Sort by salary (highest first)
  /dp-transform - Select name, department, salary fields

💡 Just type one of the commands above - no copy/paste needed!
```

### Step 3: Run a Demo Command

```
You > /dp-aggregate
```

**That's it!** The command automatically:
1. Loads the 8 employee records
2. Runs aggregation (count, avg, min, max, sum)
3. Shows the results

---

## All Available Shortcuts

| Command | What It Does | Data |
|---------|-------------|------|
| `/dp-aggregate` | Calculate statistics (count, avg, min, max, sum) | 8 employees |
| `/dp-filter` | Filter Engineering department only | 8 employees |
| `/dp-sort` | Sort by salary (highest first) | 8 employees |
| `/dp-transform` | Select name, department, salary fields | 8 employees |

---

## Example Session

```bash
$ python3 test_orchestrator_interactive.py

======================================================================
Agent Orchestrator - Interactive Testing
======================================================================

Type your query or use commands:
  /help             - Show available commands
  /load-sample-data - Show data processor commands
  /dp-aggregate     - Run data aggregation demo
  /dp-filter        - Run data filter demo
  /stats            - Show orchestrator statistics
  /quit             - Exit the session

======================================================================

You > /dp-aggregate

Running: Aggregate employee data (count, avg, min, max, sum)

[Request #1]
AI validated rule selection (confidence=0.95)

✅ SUCCESS

Agents Used: data_processor
Execution Time: 0.234s

Data Processor:
  Operation: aggregate
  Input: 8 records
  Output: 1 result

  Result:
    {
      "count": 8,
      "salary_avg": 79750.0,
      "salary_min": 55000,
      "salary_max": 110000,
      "salary_sum": 638000,
      "years_of_service_avg": 4.0,
      "performance_rating_avg": 4.375
    }

────────────────────────────────────────────────────────────────────

You > /dp-filter

Running: Filter Engineering department

✅ SUCCESS

Data Processor:
  Operation: filter
  Input: 8 records
  Output: 4 records

  Result:
    [
      {"name": "Alice Johnson", "department": "Engineering", ...},
      {"name": "Bob Smith", "department": "Engineering", ...},
      {"name": "Eve Williams", "department": "Engineering", ...},
      {"name": "Henry Wilson", "department": "Engineering", ...}
    ]

────────────────────────────────────────────────────────────────────

You > /dp-sort

Running: Sort by salary (highest first)

✅ SUCCESS

Data Processor:
  Top 5 Earners:
    1. Henry Wilson: $110,000
    2. Alice Johnson: $95,000
    3. Eve Williams: $90,000
    4. Charlie Davis: $85,000
    5. Diana Prince: $80,000

────────────────────────────────────────────────────────────────────

You > /quit

Goodbye!
```

---

## Why This Solution?

### ❌ Old Way (Doesn't Work)
```
You > {"query": "aggregate...", "data": [very long array that gets truncated]...}
```
- Terminal input buffer limits
- JSON gets truncated mid-paste
- Frustrating to debug

### ✅ New Way (Works!)
```
You > /dp-aggregate
```
- Short command (no buffer issues)
- Loads data from file automatically
- Works every time

---

## All Commands Reference

### Data Processor Commands

```bash
/load-sample-data   # Show available shortcuts
/dp-aggregate       # Calculate statistics
/dp-filter          # Filter by department
/dp-sort            # Sort by salary
/dp-transform       # Select fields
```

### Other Commands

```bash
/help      # Show all commands
/examples  # Show example queries
/stats     # Orchestrator statistics
/quit      # Exit
```

---

## Still Want to Paste JSON?

For **small data** (2-3 records), direct JSON works:

```json
{"query": "aggregate data", "data": [{"name": "Alice", "salary": 95000}, {"name": "Bob", "salary": 65000}], "operation": "aggregate", "filters": {"aggregations": ["count", "avg"]}}
```

But for **8+ records**, use the shortcuts!

---

## What's Happening Behind the Scenes?

When you type `/dp-aggregate`:

1. **Loads** `examples/sample_data.json` (8 employee records)
2. **Creates** JSON request with all data
3. **Routes** through AI-validated orchestrator
4. **Invokes** data_processor agent
5. **Shows** formatted results

All automatically - no manual JSON construction!

---

## Troubleshooting

### Issue: "Sample data not found"

**Fix:**
```bash
# Make sure you're in the project root
ls examples/sample_data.json  # Should exist

# If not found:
cd /path/to/agentOchestrator
python3 test_orchestrator_interactive.py
```

### Issue: Command not recognized

**Symptom:**
```
Unknown command: /dp-aggregate
```

**Fix:**
- Make sure you're running the updated script
- Try `/help` to see all commands
- Check for typos (case-sensitive)

---

## Summary

**Before:** 😫 Can't paste long JSON
**After:** 😊 Just type `/dp-aggregate`

**Quick Test:**
```bash
python3 test_orchestrator_interactive.py
You > /dp-aggregate
# Should work immediately!
```

---

**Created:** January 19, 2026
**Status:** ✅ Ready to use
**No more paste frustration!** 🎉
