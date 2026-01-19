# AI Validation of Rule-Based Agent Selection

## Overview

The orchestrator now includes **AI validation** for rule-based agent selection. When rules match with high confidence, the AI validates the selection before invoking agents, ensuring the right agents are called even when rule patterns might be ambiguous.

---

## How It Works

### Flow Diagram

```
User Input
    ↓
Rule Engine Matches
    ↓
High Confidence Match? ──NO──> Use AI Reasoning
    ↓ YES
AI Validates Rule Selection
    ↓
Valid? ──NO──> Use AI-Suggested Agents
    ↓ YES
Invoke Rule-Selected Agents
```

### Detailed Flow

1. **Rule Engine Evaluation**
   - Input is evaluated against all rules
   - Rules that match are ranked by priority and confidence

2. **AI Validation Step** (NEW!)
   - If rule(s) match with high confidence (≥0.7), AI is consulted
   - AI receives:
     - Original user input
     - Rule-selected agents
     - Available agent capabilities
   - AI validates if the selection is appropriate

3. **Decision Points**
   - **AI Validates** (`is_valid: true`): Use rule-selected agents
   - **AI Rejects** (`is_valid: false`): Use AI-suggested agents instead
   - **AI Error**: Default to accepting rule selection (safe fallback)

4. **Agent Invocation**
   - Selected agents are called with the input
   - Results are validated against schemas

---

## Benefits

### 1. **Prevents Incorrect Multi-Agent Calls**

**Before AI Validation:**
```
Query: "transform employee data"
Rule Matched: math_queries (because "operation" field exists)
Rule Matched: data_processing
Result: Both calculator AND data_processor invoked ❌
```

**With AI Validation:**
```
Query: "transform employee data"
Rules Matched: data_processing
AI Validates: "data_processor is appropriate, no calculator needed"
Result: Only data_processor invoked ✅
```

### 2. **Catches Rule Mismatches**

If a rule incorrectly matches due to keyword overlap, AI can catch and correct it:

```
Query: "search for the average of these numbers"
Rule Matched: search_queries (keyword "search")
AI Validates: "This is math, not document search"
AI Suggests: ["calculator"]
Result: Calculator invoked instead ✅
```

### 3. **Maintains Speed When Rules Are Correct**

- AI validation is fast (< 5 seconds)
- Only runs when rules match (not for every request)
- Rules are still the primary routing mechanism

---

## Configuration

No configuration changes required! The feature is enabled by default in `HYBRID` mode.

### Reasoning Modes

The AI validation behavior depends on the orchestrator's reasoning mode:

| Mode | Behavior |
|------|----------|
| `RULE` | No AI validation (rule-only) |
| `AI` | No rules, AI only |
| `HYBRID` | **AI validates rule decisions** ✅ |

Set in `config/orchestrator.yaml`:
```yaml
orchestrator:
  reasoning_mode: "hybrid"  # AI validation enabled
  rule_confidence_threshold: 0.7
```

---

## Logging

AI validation is fully logged for transparency and debugging:

### Example Log Output

```
2026-01-19 10:01:19 - INFO - Rule engine matched with high confidence (0.95), validating with AI
2026-01-19 10:01:23 - INFO - AI validation: is_valid=True, confidence=0.95
2026-01-19 10:01:23 - INFO - AI validated rule selection (confidence=0.95):
  The selected agent 'data_processor' is highly appropriate for this request.
  The user is asking to transform employee data with aggregation operations...
2026-01-19 10:01:23 - INFO - Reasoning complete: 1 agent(s) selected (method=rule_validated, confidence=0.95)
```

### Log Levels

- **INFO**: Normal validation flow
- **WARNING**: AI rejected rule selection, using AI suggestions instead
- **ERROR**: AI validation failed (defaults to accepting rule selection)

---

## Validation Response Format

The AI returns structured validation results:

```json
{
  "is_valid": true,
  "confidence": 0.95,
  "reasoning": "Detailed explanation of why the selection is valid/invalid",
  "suggested_agents": []
}
```

**When AI Rejects:**
```json
{
  "is_valid": false,
  "confidence": 0.85,
  "reasoning": "Rule selected calculator but this is a data processing task",
  "suggested_agents": ["data_processor"]
}
```

---

## Reasoning Method Tracking

The reasoning method in the response indicates how agents were selected:

| Method | Meaning |
|--------|---------|
| `rule_validated` | Rule matched, AI validated ✅ |
| `rule_multi_validated` | Multiple rules, AI validated |
| `ai_override` | AI rejected rule, using AI agents |
| `rule` | Rule-only (no AI validation) |
| `ai` | AI-only reasoning |
| `hybrid` | AI reasoning (no high-confidence rule) |

**Check in logs:**
```
INFO - Reasoning complete: 1 agent(s) selected (method=rule_validated, confidence=0.95)
```

---

## Examples

### Example 1: AI Validates Rule Selection

**Input:**
```json
{
  "query": "transform employee data",
  "data": [...],
  "operation": "aggregate",
  "filters": {"aggregations": ["count", "avg"]}
}
```

**Flow:**
1. Rule `data_processing` matches (priority 105, confidence 0.95)
2. AI validates: "data_processor is appropriate for this data aggregation task"
3. Result: `data_processor` invoked ✅

**Log:**
```
Rule engine matched with high confidence (0.95), validating with AI
AI validation: is_valid=True, confidence=0.95
AI validated rule selection: data_processor is highly appropriate...
```

### Example 2: AI Overrides Rule Selection

**Hypothetical Input:**
```json
{
  "query": "calculate the total and search for documentation",
  "numbers": [10, 20, 30]
}
```

**Flow:**
1. Rules match: `math_queries` AND `search_queries`
2. AI validates: "This is actually just math, no search needed"
3. AI suggests: `["calculator"]`
4. Result: Only `calculator` invoked ✅

**Log:**
```
Multiple rules matched with high confidence, validating with AI
AI rejected multi-agent selection: Only math calculation required
Using AI-suggested agents instead: ['calculator']
```

---

## Testing

Test AI validation with the included test script:

```bash
python3 test_data_processor_routing.py
```

**Expected Output:**
```
Rule engine matched with high confidence (0.95), validating with AI
AI validation: is_valid=True, confidence=0.95
✅ Success!
Agents called: ['data_processor']
```

---

## Performance Impact

### API Calls

- **Rule-only mode**: 0 AI calls
- **Hybrid mode with rule match**: 1 AI call for validation (< 5 seconds)
- **Hybrid mode without rule match**: 1 AI call for reasoning

### Cost Estimate

Using Claude Sonnet 4.5:
- Validation call: ~500 tokens input, ~200 tokens output
- Cost per validation: ~$0.002 USD
- Minimal impact on overall cost

---

## Troubleshooting

### Issue: AI Always Accepts Rule Selection

**Symptom:** AI validation never rejects rules

**Cause:** Rules are well-tuned and matching correctly

**Action:** No action needed - this is good!

### Issue: AI Validation Taking Too Long

**Symptom:** Requests take >10 seconds

**Cause:** Network latency to Anthropic API

**Solution:**
1. Check network connection
2. Consider switching to `RULE` mode for faster responses
3. Increase timeout in `config/orchestrator.yaml`

### Issue: AI Validation Errors

**Symptom:** Logs show "AI validation failed"

**Cause:** API key issue or parsing error

**Solution:**
1. Check `ANTHROPIC_API_KEY` in `.env`
2. Review logs for detailed error message
3. System defaults to accepting rule selection (safe fallback)

---

## Advanced: Multi-Agent Validation

When multiple rules match (multi-intent queries), AI validates the combined agent selection:

**Example:**
```
Rules Matched: ['data_processing', 'web_search_queries']
Agents Selected: ['data_processor', 'tavily_search']
AI Validates: "Both agents needed for this multi-intent query"
Result: Both agents invoked in parallel ✅
```

**Log:**
```
Multiple rules matched with high confidence (avg=0.88), validating with AI
AI validated multi-agent selection (confidence=0.90)
```

---

## Integration with Existing Code

The AI validation integrates seamlessly with existing code:

- **No API changes**: Existing orchestrator.process() calls work unchanged
- **Backward compatible**: Can disable by setting mode to `RULE`
- **Transparent**: All validation logged for debugging

---

## Summary

✅ **What Changed:**
- Rule-based routing now validated by AI before agent invocation
- AI can override incorrect rule selections
- Full transparency via logging

✅ **Benefits:**
- Prevents multi-agent routing errors
- Catches rule mismatches
- Maintains speed when rules are correct

✅ **No Breaking Changes:**
- Existing code works unchanged
- Feature enabled by default in HYBRID mode
- Can disable by switching to RULE mode

---

**Created:** January 19, 2026
**Version:** 1.0
**Status:** ✅ Production Ready
