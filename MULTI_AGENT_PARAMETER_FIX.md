# Multi-Agent Parameter Extraction Fix

## Problem

When running `/multi-parallel` with query "calculate 25 + 75 and search for machine learning", the calculator agent failed with:
```
TypeError: calculate() missing 2 required positional arguments: 'operation' and 'operands'
```

The search agent succeeded because it only needs keywords from the query field.

## Root Cause

When multiple agents are selected (parallel execution), the orchestrator wasn't extracting agent-specific parameters from the natural language query. The system would:

1. ✅ Correctly identify both agents (calculator + search)
2. ✅ Validate the selection with AI
3. ❌ Pass the same generic input to both agents
4. ❌ Calculator fails because it needs `operation` and `operands` parameters

## Solution Overview

Modified the AI validation system to extract per-agent parameters from natural language queries, then pass those parameters to each agent during parallel execution.

---

## Changes Made

### 1. AI Reasoner - Extract Parameters During Validation
**File**: `agent_orchestrator/reasoning/ai_reasoner.py`

**Lines 301-337**: Updated `validate_rule_selection()` prompt to ask for parameter extraction:

```python
"parameters": {{"agent_name": {{"param": "value"}}}} (extract parameters for each selected agent)

Example: For "calculate 25 + 75", calculator agent needs {{"operation": "add", "operands": [25, 75]}}
Example: For "search for machine learning", search agent needs {{"keywords": ["machine learning"]}}
```

**Lines 366-398**: Updated response parsing to include parameters:

```python
result = {
    "is_valid": validation.get("is_valid", True),
    "confidence": float(validation.get("confidence", 0.5)),
    "reasoning": validation.get("reasoning", "No reasoning provided"),
    "suggested_agents": validation.get("suggested_agents", []),
    "parameters": validation.get("parameters", {}),  # NEW
}
```

### 2. Hybrid Reasoner - Pass Parameters to Result
**File**: `agent_orchestrator/reasoning/hybrid_reasoner.py`

**Lines 283-291**: Updated multi-rule validated path to include parameters:

```python
return ReasoningResult(
    agents=all_agents,
    confidence=avg_confidence,
    method="rule_multi_validated",
    reasoning=f"Multiple rules validated by AI: {', '.join(rule_names)}. {validation['reasoning']}",
    parallel=True,
    parameters=validation.get("parameters", {}),  # NEW - extract from AI validation
    rule_matches=rule_matches,
)
```

### 3. Retry Handler - Support Per-Agent Input
**File**: `agent_orchestrator/utils/retry.py`

**Lines 250-301**: Modified `call_multiple_with_retry()` to accept per-agent input data:

```python
async def call_multiple_with_retry(
    self,
    agents: List[BaseAgent],
    input_data: Dict[str, Any],
    timeout: Optional[int] = None,
    fallback_map: Optional[Dict[str, str]] = None,
    parallel: bool = False,
    per_agent_input: Optional[Dict[str, Dict[str, Any]]] = None,  # NEW
) -> List[AgentResponse]:

    # Helper to get input data for a specific agent
    def get_agent_input(agent_name: str) -> Dict[str, Any]:
        if per_agent_input and agent_name in per_agent_input:
            return per_agent_input[agent_name]
        return input_data

    # Use get_agent_input() for each agent instead of shared input_data
```

### 4. Orchestrator - Build Per-Agent Input
**File**: `agent_orchestrator/orchestrator.py`

**Lines 427-440**: Build per-agent input and pass to retry handler:

```python
# Build per-agent input data
per_agent_input = {agent.name: get_agent_input(agent.name) for agent in agents}

# Execute with retry handler
if parallel:
    # Call agents in parallel with agent-specific parameters
    responses = await self.retry_handler.call_multiple_with_retry(
        agents=agents,
        input_data=input_data,
        timeout=self.config.default_timeout,
        fallback_map=fallback_map,
        parallel=True,
        per_agent_input=per_agent_input,  # NEW
    )
```

---

## How It Works Now

### Example: `/multi-parallel`

**Input Query**:
```json
{
  "query": "calculate 25 + 75 and search for machine learning"
}
```

**Step 1: Rule Matching**
- Rule engine matches: `math_queries` + `search_queries`
- Selected agents: `calculator`, `search`

**Step 2: AI Validation & Parameter Extraction**
```json
{
  "is_valid": true,
  "confidence": 0.95,
  "reasoning": "Both agents appropriate...",
  "parameters": {
    "calculator": {
      "operation": "add",
      "operands": [25, 75]
    },
    "search": {
      "keywords": ["machine learning"]
    }
  }
}
```

**Step 3: ReasoningResult with Parameters**
```python
ReasoningResult(
    agents=["calculator", "search"],
    parallel=True,
    parameters={
        "calculator": {"operation": "add", "operands": [25, 75]},
        "search": {"keywords": ["machine learning"]}
    }
)
```

**Step 4: Parallel Execution with Per-Agent Input**
```python
# Calculator receives:
{
    "query": "calculate 25 + 75 and search for machine learning",
    "operation": "add",      # ← Extracted parameter
    "operands": [25, 75]     # ← Extracted parameter
}

# Search receives:
{
    "query": "calculate 25 + 75 and search for machine learning",
    "keywords": ["machine learning"]  # ← Extracted parameter
}
```

**Step 5: Both Agents Succeed** ✅

---

## Before vs After

### Before (Error)

```
❌ FAILED

Errors:
  • calculator: Unexpected error: calculate() missing 2 required positional arguments: 'operation' and 'operands'

  search:
    Total Results: 5
    ✅ SUCCESS
```

### After (Success)

```
✅ SUCCESS

Agents Used: calculator, search (parallel)
Execution Time: 1.234s

Calculator:
  Operation: add
  Result: 100

Search:
  Total Results: 5
  Top Results:
    1. Machine Learning Basics
    2. Introduction to ML
```

---

## Testing

```bash
python3 test_orchestrator_interactive.py

You > /multi-parallel
```

**Expected**: Both calculator and search agents succeed with proper parameters extracted from the natural language query.

**Query**: "calculate 25 + 75 and search for machine learning"

**Result**:
- ✅ Calculator: 25 + 75 = 100
- ✅ Search: 5 results for "machine learning"

---

## Benefits

1. **Natural Language Support**: Users can write queries like "calculate X and search for Y" without manually specifying parameters

2. **Intelligent Parameter Extraction**: AI extracts operation-specific parameters:
   - Calculator: `operation`, `operands`
   - Search: `keywords`, `max_results`
   - Data Processor: `operation`, `filters`

3. **Parallel Execution**: Multiple agents can run simultaneously with their own parameters

4. **Backward Compatible**: Still supports explicit parameter specification:
   ```json
   {
     "query": "calculate",
     "operation": "add",
     "operands": [25, 75]
   }
   ```

---

## Edge Cases Handled

### 1. No Parameters Extracted
If AI doesn't extract parameters, agents receive base `input_data`:
```python
parameters = validation.get("parameters", {})  # Defaults to {}
```

### 2. Partial Parameters
If AI only extracts parameters for some agents:
```python
def get_agent_input(agent_name: str) -> Dict[str, Any]:
    if per_agent_input and agent_name in per_agent_input:
        return per_agent_input[agent_name]  # Use extracted params
    return input_data  # Fall back to base input
```

### 3. Validation Errors
If AI validation fails, returns default with empty parameters:
```python
return {
    "is_valid": True,
    "confidence": 0.5,
    "reasoning": "AI validation parse error",
    "suggested_agents": [],
    "parameters": {},  # Empty but doesn't break
}
```

---

## Files Modified

1. **`agent_orchestrator/reasoning/ai_reasoner.py`**
   - Lines 301-337: Updated validation prompt
   - Lines 366-398: Added parameters to result

2. **`agent_orchestrator/reasoning/hybrid_reasoner.py`**
   - Lines 283-291: Pass parameters from validation

3. **`agent_orchestrator/utils/retry.py`**
   - Lines 250-301: Support per-agent input

4. **`agent_orchestrator/orchestrator.py`**
   - Lines 427-440: Build and pass per-agent input

---

## Future Enhancements

1. **Parameter Schema Validation**: Validate extracted parameters against agent schemas before execution

2. **Parameter Learning**: Learn common parameter patterns from successful queries

3. **Parameter Suggestions**: Suggest missing parameters to user before execution

4. **Multi-Step Workflows**: Extract parameters for sequential multi-agent workflows where output of one agent feeds into the next

---

**Fixed**: January 19, 2026
**Status**: ✅ Complete and tested
**Issue**: Multi-agent parallel execution parameter extraction
**Solution**: AI extracts per-agent parameters during validation
