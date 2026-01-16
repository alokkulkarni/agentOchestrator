# Response Validation and Per-Query Logging

## Overview

The Agent Orchestrator includes comprehensive response validation, hallucination detection, and detailed per-query logging to ensure response quality and provide complete audit trails.

### Key Features

✅ **Response Validation** - Validates agent responses against the original user query
✅ **Hallucination Detection** - Detects fabricated or contradictory information
✅ **Confidence Scoring** - Calculates confidence scores (logged, never sent to users)
✅ **Automatic Retry** - Retries agent calls when validation fails
✅ **Comprehensive Logging** - Logs every decision, interaction, and validation per query
✅ **Cross-Agent Consistency** - Validates consistency across multiple agent outputs

---

## How It Works

### Validation Pipeline

```
User Query
    ↓
Orchestrator
    ↓
├─→ Reasoning (select agents)
│   └─→ Log decision
    ↓
├─→ Execute Agents
│   └─→ Log each interaction
    ↓
├─→ Validate Response
│   ├─→ Check relevance to query
│   ├─→ Detect hallucinations
│   ├─→ Check consistency
│   └─→ Calculate confidence
    ↓
├─→ Validation Pass?
│   ├─→ YES: Return response
│   └─→ NO:  Retry (up to max_retries)
    ↓
├─→ Log Everything
│   ├─→ Reasoning decisions
│   ├─→ Agent interactions
│   ├─→ Validation results
│   ├─→ Confidence scores
│   ├─→ Retry attempts
│   └─→ Errors
    ↓
User Response (NO confidence score)
```

---

## Configuration

### orchestrator.yaml

```yaml
# Response validation and hallucination detection
validation_confidence_threshold: 0.7  # Minimum confidence (0.0-1.0)
validation_max_retries: 2  # Retry attempts when validation fails

# Per-query logging
query_log_dir: "logs/queries"  # Directory for query logs
log_queries_to_file: true  # Enable detailed logging
log_queries_to_console: false  # Show summaries in console
```

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `validation_confidence_threshold` | float | 0.7 | Minimum confidence score (0.0-1.0) for validation to pass |
| `validation_max_retries` | int | 2 | Maximum retry attempts when validation fails (0-5) |
| `query_log_dir` | string | "logs/queries" | Directory for per-query log files |
| `log_queries_to_file` | bool | true | Enable detailed per-query logging to files |
| `log_queries_to_console` | bool | false | Show query summaries in console output |

---

## Validation Components

### 1. Basic Validation

Checks fundamental response correctness:
- ✅ Responses are not empty
- ✅ Required fields are present
- ✅ Data types are correct
- ✅ No obvious errors in response

### 2. Cross-Agent Consistency

For multi-agent workflows, validates:
- ✅ No contradictory information between agents
- ✅ Data counts align (e.g., search returned N, processor handled N)
- ✅ Numeric results are reasonable (no extreme variances)
- ✅ Data formats are consistent

### 3. Hallucination Detection

**Rule-Based Detection:**
- Calculator returning infinity or impossible results
- Search results unrelated to query keywords
- Operations mismatched with query (e.g., query says "add" but operation is "multiply")

**AI-Based Detection** (when enabled):
- Uses Claude to evaluate response relevance
- Checks for fabricated information
- Validates factual consistency
- Identifies contradictions

### 4. Confidence Scoring

Confidence score (0.0-1.0) based on:
- Basic validation passed (+base confidence)
- Consistency check passed (+0.2)
- No hallucination detected (+0.4)
- Response completeness (+0.2 max)

**⚠️ IMPORTANT**: Confidence scores are **ONLY logged**, **NEVER sent to users**.

---

## Per-Query Logging

### What Gets Logged

Every query generates a detailed JSON log file containing:

1. **Query Information**
   - Query ID (UUID)
   - Timestamp
   - Original user query and parameters

2. **Reasoning Decision**
   - Reasoning mode (rule/AI/hybrid)
   - Method used (which reasoner)
   - Selected agents
   - Confidence in agent selection
   - Explanation/reasoning text
   - Parallel vs sequential execution

3. **Agent Interactions**
   - Agent name
   - Input sent to agent
   - Output received from agent
   - Success/failure status
   - Execution time (ms)
   - Error messages (if failed)

4. **Tool Interactions** (if applicable)
   - Tool name
   - Tool input
   - Tool output
   - Execution time

5. **Validation Results**
   - Is valid (true/false)
   - **Confidence score** (0.0-1.0)
   - Hallucination detected (true/false)
   - Validation details:
     - Basic validation results
     - Consistency check results
     - Hallucination detection details
     - AI validation scores (if enabled)
   - Issues found (list)
   - Retry on failure (true/false)

6. **Retry Attempts**
   - Attempt number
   - Reason for retry
   - Agents being retried
   - Timestamp

7. **Errors**
   - Error type
   - Error message
   - Error details
   - Timestamp

8. **Timing**
   - Start time
   - End time
   - Total duration (ms)

9. **Final Result**
   - Success status
   - Agents used
   - Error count

### Log File Format

**Filename**: `query_<timestamp>_<query_id_prefix>.json`

**Example**: `query_2026-01-16T10-30-45_abc123de.json`

**Location**: `logs/queries/`

### Log File Example

```json
{
  "query_id": "abc123de-f456-7890-gh12-ijk345lm6789",
  "timestamp": "2026-01-16T10:30:45.123456",
  "user_query": {
    "query": "calculate 15 + 27",
    "operation": "add",
    "operands": [15, 27]
  },
  "reasoning": {
    "mode": "hybrid",
    "timestamp": "2026-01-16T10:30:45.234567",
    "selected_agents": ["calculator"],
    "confidence": 0.9,
    "method": "rule",
    "reasoning_text": "Matched calculation rule with high confidence",
    "parallel": false,
    "parameters": {}
  },
  "agent_interactions": [
    {
      "agent_name": "calculator",
      "timestamp": "2026-01-16T10:30:45.345678",
      "input": {
        "query": "calculate 15 + 27",
        "operation": "add",
        "operands": [15, 27]
      },
      "output": {
        "result": 42,
        "operation": "add",
        "expression": "15 + 27"
      },
      "success": true,
      "execution_time_ms": 23.456,
      "error": null
    }
  ],
  "tool_interactions": [],
  "validation": {
    "timestamp": "2026-01-16T10:30:45.456789",
    "is_valid": true,
    "confidence_score": 0.95,
    "hallucination_detected": false,
    "validation_details": {
      "basic_validation": {
        "passed": true,
        "issues": []
      },
      "consistency_check": {
        "passed": true,
        "issues": []
      },
      "hallucination_detection": {
        "rule_based_check": {
          "detected": false,
          "issues": []
        },
        "ai_based_check": {
          "relevance_score": 0.98,
          "accuracy_score": 1.0,
          "hallucination_detected": false
        },
        "final_decision": false
      },
      "confidence_calculation": {
        "score": 0.95,
        "threshold": 0.7,
        "meets_threshold": true
      }
    },
    "issues": [],
    "retry_on_failure": false
  },
  "retry_attempts": [],
  "errors": [],
  "timing": {
    "start_time": "2026-01-16T10:30:45.123456",
    "end_time": "2026-01-16T10:30:45.567890",
    "total_duration_ms": 444.434
  },
  "final_result": {
    "success": true,
    "agent_count": 1,
    "agents_used": ["calculator"],
    "error_count": 0
  }
}
```

---

## Retry Logic

### When Retries Occur

Automatic retry happens when:
- ✅ Basic validation fails
- ✅ Consistency check fails
- ✅ Hallucination detected
- ✅ Confidence score below threshold

### Retry Behavior

1. **Attempt 1**: Initial agent execution
2. **Validation Fails**: Log validation issues
3. **Attempt 2**: Retry with same agents
4. **Validation Fails**: Log retry attempt
5. **Attempt 3**: Final retry (if max_retries=2)
6. **Max Retries Exceeded**: Return best effort result with warning

### Best Effort Response

If validation fails after all retries:
- Response is still returned (not blocked)
- Warning added to `_metadata.validation_warning`
- Full details logged (but confidence score NOT in response)

```json
{
  "success": true,
  "data": { /* agent outputs */ },
  "_metadata": {
    "validation_warning": {
      "message": "Response validation failed after retries",
      "issues": ["List of validation issues"],
      "hallucination_detected": false
    }
  }
}
```

---

## Reading Query Logs

### Using QueryLogReader

```python
from agent_orchestrator.utils import QueryLogReader

# Create reader
reader = QueryLogReader(log_dir="logs/queries")

# Get recent queries
recent_logs = reader.get_recent_queries(limit=10)

for log in recent_logs:
    print(f"Query: {log['user_query']['query']}")
    print(f"Success: {log['final_result']['success']}")
    print(f"Confidence: {log['validation']['confidence_score']}")
    print()

# Get specific query by ID
query_log = reader.get_query_by_id("abc123de")

# Get statistics
stats = reader.get_stats()
print(f"Total Queries: {stats['total_queries']}")
print(f"Success Rate: {stats['success_rate']:.1%}")
print(f"Avg Confidence: {stats['avg_confidence']:.3f}")
print(f"Hallucination Rate: {stats['hallucination_rate']:.1%}")
```

### Statistics Available

- `total_queries`: Total number of queries logged
- `success_rate`: Percentage of successful queries
- `avg_duration_ms`: Average query duration in milliseconds
- `avg_confidence`: Average confidence score across queries
- `hallucination_rate`: Percentage of queries with hallucinations detected
- `retry_rate`: Percentage of queries that required retries

---

## Examples

### Example 1: Simple Query (Validation Passes)

**Query:**
```python
result = await orchestrator.process({
    "query": "calculate 2 + 2",
    "operation": "add",
    "operands": [2, 2]
})
```

**Flow:**
1. Reasoning selects `calculator` agent
2. Calculator executes: `2 + 2 = 4`
3. Validation checks:
   - ✅ Result present
   - ✅ No hallucination
   - ✅ Confidence: 0.95
4. Validation **passes** → return response
5. Log file created with all details

**User Response** (NO confidence score):
```json
{
  "success": true,
  "data": {
    "calculator": {
      "result": 4,
      "operation": "add"
    }
  }
}
```

**Log File** (HAS confidence score):
```json
{
  "validation": {
    "is_valid": true,
    "confidence_score": 0.95,
    ...
  }
}
```

### Example 2: Multi-Agent Query (Retry Required)

**Query:**
```python
result = await orchestrator.process({
    "query": "search for AI papers and analyze sentiment"
})
```

**Flow:**
1. Reasoning selects `search` + `data_processor`
2. **Attempt 1**:
   - Search returns 5 papers
   - Data processor returns 3 sentiment scores
   - Validation: ❌ Consistency failure (count mismatch)
   - Confidence: 0.55 (below threshold)
3. **Retry 1**:
   - Re-execute both agents
   - Search returns 5 papers
   - Data processor returns 5 sentiment scores
   - Validation: ✅ Pass
   - Confidence: 0.87
4. Return response

**Log File Shows:**
- Initial attempt with validation failure
- Retry attempt logged with reason
- Second validation success
- All agent interactions logged

---

## Benefits

### 1. Response Quality

- **Validation**: Ensures responses answer the actual query
- **Hallucination Detection**: Catches fabricated information
- **Consistency**: Multi-agent outputs align correctly
- **Retry**: Automatically recovers from validation failures

### 2. Debugging & Monitoring

- **Complete Audit Trail**: Every decision and interaction logged
- **Confidence Tracking**: Monitor response quality over time
- **Error Analysis**: Identify patterns in failures
- **Performance Metrics**: Execution times, success rates

### 3. Compliance & Security

- **Full Audit**: Complete record of all agent actions
- **Confidence Scores**: Internal quality metrics (not exposed)
- **Validation Warnings**: Transparent about quality issues
- **Per-Query Isolation**: Each query independently logged

### 4. Analytics

- Success rates over time
- Average confidence scores
- Hallucination detection rates
- Retry patterns
- Agent performance metrics
- Validation failure reasons

---

## Best Practices

### 1. Configuration

- **Threshold**: Set `validation_confidence_threshold` based on your quality requirements
  - `0.5-0.6`: Permissive (fewer retries, faster responses)
  - `0.7-0.8`: Balanced (recommended)
  - `0.9-1.0`: Strict (more retries, higher quality)

- **Retries**: Adjust `validation_max_retries` based on your latency tolerance
  - `0-1`: Fast responses, lower quality assurance
  - `2`: Balanced (recommended)
  - `3-5`: Higher quality, slower responses

### 2. Monitoring

- Regularly review query logs for patterns
- Monitor `avg_confidence` in statistics
- Track `hallucination_rate` over time
- Alert on high retry rates

### 3. Log Management

- Query logs can grow large over time
- Implement log rotation or archival
- Consider aggregating statistics periodically
- Use `QueryLogReader.get_stats()` for monitoring

### 4. AI Validation

- AI-based validation requires `ANTHROPIC_API_KEY`
- Adds latency (~500ms) but improves accuracy
- Falls back to rule-based if API unavailable
- Most effective for complex or ambiguous queries

---

## Testing

### Run Test Suite

```bash
# Test validation and logging
python3 test_validation_and_logging.py
```

### Tests Included

1. ✅ Basic Validation - Simple calculator query
2. ✅ Search Validation - Complex search query
3. ✅ Log Inspection - Verify log file contents
4. ✅ Confidence Not in Response - Ensure scores stay internal

---

## API Reference

### ResponseValidator

```python
from agent_orchestrator.validation import ResponseValidator

validator = ResponseValidator(
    anthropic_api_key="your_key",
    enable_ai_validation=True,
    confidence_threshold=0.7
)

result = await validator.validate_response(
    user_query={"query": "..."},
    agent_responses={"agent_name": {...}},
    reasoning={...}
)

print(result.is_valid)
print(result.confidence_score)
print(result.hallucination_detected)
```

### QueryLogger

```python
from agent_orchestrator.utils import QueryLogger

logger = QueryLogger(
    log_dir="logs/queries",
    log_to_file=True,
    log_to_console=False
)

# Create query context
context = logger.create_query_context(user_query)

# Log reasoning
logger.log_reasoning(context, mode, result)

# Log agent interaction
logger.log_agent_interaction(
    context, agent_name, input, output,
    success, execution_time_ms
)

# Log validation
logger.log_validation(context, validation_result)

# Finalize log
logger.finalize_query_log(context, final_result)
```

---

## Troubleshooting

### Issue: Validation Always Fails

**Solution:**
- Check `validation_confidence_threshold` (lower it)
- Review log files to see specific issues
- Ensure agents are returning complete data
- Verify query format is correct

### Issue: Too Many Retries

**Solution:**
- Increase `validation_confidence_threshold` (less strict)
- Reduce `validation_max_retries`
- Check if agents are consistently failing
- Review hallucination detection rules

### Issue: No Log Files Generated

**Solution:**
- Check `log_queries_to_file` is `true`
- Verify `query_log_dir` path is writable
- Ensure orchestrator is initialized
- Check for errors in console output

### Issue: AI Validation Not Working

**Solution:**
- Verify `ANTHROPIC_API_KEY` is set
- Check `reasoning_mode` is "ai" or "hybrid"
- Review API rate limits
- Falls back to rule-based validation

---

## Summary

The validation and logging system provides:

✅ **Quality Assurance** - Validates every response
✅ **Hallucination Detection** - Catches fabricated information
✅ **Automatic Recovery** - Retries on validation failure
✅ **Complete Audit Trail** - Logs everything per query
✅ **Privacy** - Confidence scores never sent to users
✅ **Monitoring** - Statistics and analytics built-in

All this happens **automatically** with zero code changes required. Just configure thresholds in `orchestrator.yaml` and start querying!

---

**Status**: ✅ Complete and Production-Ready
**Created**: January 16, 2026
**Version**: 1.0
