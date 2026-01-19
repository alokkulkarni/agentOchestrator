# Test Commands Reference

Complete reference for all test commands in the interactive orchestrator.

## Quick Start

```bash
python3 test_orchestrator_interactive.py
```

Then type `/help` to see all commands or `/examples` to see examples.

---

## Quick Test Commands (Comprehensive)

These commands run multiple operations to demonstrate all capabilities:

### `/test-all-dp`
**Runs all 4 data processor operations sequentially**

Tests in order:
1. **Transform**: Select name, department, salary fields
2. **Filter**: Filter Engineering department only
3. **Aggregate**: Calculate count, avg, min, max, sum
4. **Sort**: Sort by salary (descending)

**Output**: Shows results for each operation with formatted display

### `/test-all-calc`
**Runs all 5 calculator operations sequentially**

Tests in order:
1. **Add**: 15 + 27 = 42
2. **Subtract**: 100 - 35 = 65
3. **Multiply**: 8 × 12 = 96
4. **Divide**: 144 ÷ 12 = 12
5. **Average**: avg([10, 20, 30, 40, 50]) = 30

**Output**: Shows result and explanation for each operation

---

## Data Processor Commands

Test individual data processing operations on 8 employee records.

### `/load-sample-data` (alias: `/sample`)
**Shows available data processor shortcuts and sample data preview**

Displays:
- 8 employee records from `examples/sample_data.json`
- Available quick commands
- Sample data structure

### `/dp-aggregate`
**Run aggregate operation**

Calculates:
- Count of records
- Average salary, years of service, performance rating
- Min/max salary
- Sum of salaries

**Example Output**:
```json
{
  "count": 8,
  "salary_avg": 79750.0,
  "salary_min": 55000,
  "salary_max": 110000,
  "salary_sum": 638000
}
```

### `/dp-filter`
**Run filter operation**

Filters employees in Engineering department only.

**Example Output**: 4 employees (Alice, Bob, Eve, Henry)

### `/dp-sort`
**Run sort operation**

Sorts employees by salary in descending order.

**Example Output**: List sorted from highest ($110k) to lowest ($55k)

### `/dp-transform`
**Run transform operation**

Selects only name, department, and salary fields.

**Example Output**: Simplified records with 3 fields each

---

## Calculator Commands

Test calculator operations with predefined inputs.

### `/calc-add`
**Calculate 15 + 27**

**Expected Result**: 42

### `/calc-multiply`
**Calculate 8 × 12**

**Expected Result**: 96

### `/calc-average`
**Calculate average of [10, 20, 30, 40, 50]**

**Expected Result**: 30.0

---

## Search Commands

Test search agent functionality.

### `/search-test`
**Search for 'Python tutorials'**

Demonstrates:
- Keyword-based search
- Result ranking
- Metadata extraction

**Example Output**: List of relevant documents/tutorials

---

## Multi-Agent Workflow Commands

Test parallel and sequential execution of multiple agents.

### `/multi-parallel`
**Execute calculator and search agents in parallel**

Query: "calculate 25 + 75 and search for machine learning"

**Demonstrates**:
- Simultaneous execution of 2 agents
- Parallel reasoning
- Combined results

**Expected Agents**: calculator + search (executed at the same time)

### `/multi-sequential`
**Execute calculator then search agents sequentially**

Query: "calculate 50 + 50, then search for the result"

**Demonstrates**:
- Sequential execution (one after another)
- Data flow between agents
- Chained reasoning

**Expected Agents**: calculator → search (executed in order)

---

## General Commands

### `/help`
Shows comprehensive help with all commands organized by category.

### `/examples`
Shows example queries for natural language and JSON formats.

### `/stats`
Shows orchestrator statistics:
- Total requests processed
- Agent call counts and success rates
- Average execution times
- Health status

### `/quit`
Exit the interactive session.

---

## Query Formats

### 1. Short Commands (Easiest)
```
/test-all-dp
/calc-add
/search-test
```

### 2. Natural Language
```
calculate 15 + 27
search for python tutorials
find the average of 10, 20, 30
```

### 3. JSON Format (Advanced)
```json
{"query": "calculate", "operation": "add", "operands": [15, 27]}
{"query": "search", "keywords": ["python"], "max_results": 5}
{"query": "aggregate", "data": [...], "operation": "aggregate"}
```

---

## Testing Workflow

### Quick Demo (2 minutes)
```bash
# Start interactive mode
python3 test_orchestrator_interactive.py

# Run comprehensive tests
You > /test-all-dp
You > /test-all-calc

# Check stats
You > /stats
```

### Complete Testing (5 minutes)
```bash
# 1. Test data processor
You > /test-all-dp

# 2. Test calculator
You > /test-all-calc

# 3. Test search
You > /search-test

# 4. Test parallel execution
You > /multi-parallel

# 5. Test sequential execution
You > /multi-sequential

# 6. View statistics
You > /stats
```

### Individual Feature Testing
```bash
# Test specific operations
You > /dp-aggregate
You > /dp-filter
You > /calc-add
You > /calc-multiply
```

---

## Command Summary Table

| Command | Category | What It Tests | Agents Used | Duration |
|---------|----------|---------------|-------------|----------|
| `/test-all-dp` | Comprehensive | All 4 data processor ops | data_processor | ~5s |
| `/test-all-calc` | Comprehensive | All 5 calculator ops | calculator | ~5s |
| `/dp-aggregate` | Data Processor | Aggregation | data_processor | ~1s |
| `/dp-filter` | Data Processor | Filtering | data_processor | ~1s |
| `/dp-sort` | Data Processor | Sorting | data_processor | ~1s |
| `/dp-transform` | Data Processor | Transformation | data_processor | ~1s |
| `/calc-add` | Calculator | Addition | calculator | ~1s |
| `/calc-multiply` | Calculator | Multiplication | calculator | ~1s |
| `/calc-average` | Calculator | Average | calculator | ~1s |
| `/search-test` | Search | Keyword search | search | ~1s |
| `/multi-parallel` | Multi-Agent | Parallel execution | calc + search | ~1s |
| `/multi-sequential` | Multi-Agent | Sequential execution | calc + search | ~2s |

---

## Expected Output Format

All commands show:

```
Running: [Operation description]

[Request #N]
AI validated rule selection (confidence=X.XX)

✅ SUCCESS

Agents Used: [agent_name]
Execution Time: X.XXXs
Reasoning: [method used]

[Agent Name]:
  [Formatted results]

────────────────────────────────────────────────────────────────────
```

---

## Troubleshooting

### Issue: Command not recognized
**Fix**: Type `/help` to see all available commands (case-sensitive)

### Issue: Sample data not found
**Fix**: Ensure you're in the project root directory
```bash
cd /path/to/agentOchestrator
ls examples/sample_data.json  # Should exist
```

### Issue: Agent timeout
**Fix**: Check agent configuration in `config/agents.yaml`

### Issue: Validation failures
**Fix**: Check schema files in `config/schemas/`

---

## Features Demonstrated

✅ **All Agent Types**:
- Direct tool agents (calculator, search, data_processor)
- MCP server agents (if enabled)

✅ **All Reasoning Methods**:
- Rule-based selection
- AI-validated rule selection
- AI-based reasoning
- Hybrid reasoning

✅ **All Execution Modes**:
- Single agent
- Parallel multi-agent
- Sequential multi-agent

✅ **All Validation Layers**:
- Pre-execution (AI validates agent selection)
- Post-execution (JSON schema validation)
- Confidence scoring
- Hallucination detection

✅ **All Data Operations**:
- Aggregation (count, avg, min, max, sum)
- Filtering (conditions)
- Sorting (ascending/descending)
- Transformation (field selection)

---

**Created**: January 19, 2026
**Status**: ✅ All 11+ test commands implemented and documented
**Interactive Help**: Always available via `/help` in the session
