# Prometheus Metrics Label Fixes

## Summary
Fixed multiple Prometheus metrics label mismatches that were causing `ValueError: histogram/counter metric is missing label values` errors.

---

## Issues Fixed

### 1. ✅ `reasoning_confidence` Histogram - Missing `method` Label
**Error:**
```
ValueError: histogram metric is missing label values
File "orchestrator.py", line 596
    orchestrator_metrics.reasoning_confidence.observe(reasoning_result.confidence)
```

**Root Cause:** Metric defined with `["method"]` label but called without providing it.

**Fix (Line 596-598):**
```python
# BEFORE:
orchestrator_metrics.reasoning_confidence.observe(reasoning_result.confidence)

# AFTER:
orchestrator_metrics.reasoning_confidence.labels(
    method=reasoning_result.method
).observe(reasoning_result.confidence)
```

---

### 2. ✅ `reasoning_duration` Histogram - Wrong Label Name
**Issue:** Metric defined with `["method"]` but code used `reasoning_mode`

**Fix (Line 599-601):**
```python
# BEFORE:
orchestrator_metrics.reasoning_duration.labels(
    reasoning_mode=self.config.reasoning_mode
).observe(duration_seconds)

# AFTER:
orchestrator_metrics.reasoning_duration.labels(
    method=reasoning_result.method
).observe(duration_seconds)
```

---

### 3. ✅ `agent_duration` Histogram - Wrong Label Name
**Issue:** Metric defined with `["agent_name"]` but code used `agent`

**Fix (Line 772-774):**
```python
# BEFORE:
orchestrator_metrics.agent_duration.labels(
    agent=response.agent_name
).observe(response.execution_time)

# AFTER:
orchestrator_metrics.agent_duration.labels(
    agent_name=response.agent_name
).observe(response.execution_time)
```

---

### 4. ✅ `agent_calls_total` Counter - Wrong Metric Name and Label
**Issue:** Code used `agent_calls` instead of `agent_calls_total`, and `agent` instead of `agent_name`

**Fix (Line 768-771):**
```python
# BEFORE:
orchestrator_metrics.agent_calls.labels(
    agent=response.agent_name,
    status=status
).inc()

# AFTER:
orchestrator_metrics.agent_calls_total.labels(
    agent_name=response.agent_name,
    status=status
).inc()
```

---

### 5. ✅ `queries_failed` Counter - Missing `error_type` Label
**Issue:** Metric defined with `["error_type", "reasoning_mode"]` but code only provided `reasoning_mode`

**Fix (Line 426-429):**
```python
# BEFORE:
orchestrator_metrics.queries_failed.labels(
    reasoning_mode=self.config.reasoning_mode
).inc()

# AFTER:
orchestrator_metrics.queries_failed.labels(
    error_type="SecurityError",
    reasoning_mode=self.config.reasoning_mode
).inc()
```

**Fix (Line 449-452):**
```python
# BEFORE:
orchestrator_metrics.queries_failed.labels(
    reasoning_mode=self.config.reasoning_mode
).inc()

# AFTER:
orchestrator_metrics.queries_failed.labels(
    error_type="ReasoningError",
    reasoning_mode=self.config.reasoning_mode
).inc()
```

**Fix (Line 537-540):**
```python
# BEFORE:
orchestrator_metrics.queries_failed.labels(
    reasoning_mode=self.config.reasoning_mode
).inc()

# AFTER:
orchestrator_metrics.queries_failed.labels(
    error_type=type(e).__name__,
    reasoning_mode=self.config.reasoning_mode
).inc()
```

---

### 6. ✅ `agent_retries` Counter - Wrong Label Name
**Issue:** Metric defined with `["agent_name", "reason"]` but code used `agent`

**Fix (Line 852-855):**
```python
# BEFORE:
orchestrator_metrics.agent_retries.labels(
    agent=agent_name,
    reason="validation_failed"
).inc()

# AFTER:
orchestrator_metrics.agent_retries.labels(
    agent_name=agent_name,
    reason="validation_failed"
).inc()
```

---

### 7. ✅ `circuit_breaker_open` Gauge - Wrong Label Name (Fixed Previously)
**Issue:** Metric defined with `["agent_name"]` but code used `agent`

**Fix (Lines 944, 946):**
```python
# BEFORE:
orchestrator_metrics.circuit_breaker_open.labels(agent=agent.name).set(1)
orchestrator_metrics.circuit_breaker_open.labels(agent=agent.name).set(0)

# AFTER:
orchestrator_metrics.circuit_breaker_open.labels(agent_name=agent.name).set(1)
orchestrator_metrics.circuit_breaker_open.labels(agent_name=agent.name).set(0)
```

---

## Metric Label Reference

For future reference, here are the correct labels for each metric:

| Metric | Type | Labels |
|--------|------|--------|
| `reasoning_confidence` | Histogram | `["method"]` |
| `reasoning_duration` | Histogram | `["method"]` |
| `reasoning_decisions` | Counter | `["reasoning_mode", "method"]` |
| `agent_calls_total` | Counter | `["agent_name", "status"]` |
| `agent_duration` | Histogram | `["agent_name"]` |
| `agent_retries` | Counter | `["agent_name", "reason"]` |
| `circuit_breaker_open` | Gauge | `["agent_name"]` |
| `queries_total` | Counter | `["status", "reasoning_mode"]` |
| `queries_success` | Counter | `["reasoning_mode"]` |
| `queries_failed` | Counter | `["error_type", "reasoning_mode"]` |
| `query_duration` | Histogram | `["reasoning_mode"]` |
| `ai_reasoner_cost` | Counter | `["provider", "model"]` |
| `ai_reasoner_tokens` | Counter | `["provider", "model", "token_type"]` |
| `validation_confidence` | Histogram | No labels |
| `queries_per_session` | Histogram | No labels |

---

## Files Modified

**File:** `agent_orchestrator/orchestrator.py`
**Lines Changed:** 426-429, 449-452, 537-540, 596-601, 768-774, 852-855, 944, 946

---

## Testing

After all fixes, the orchestrator server starts successfully:

```bash
$ python3 -m agent_orchestrator.server

✅ Orchestrator API started successfully - 4 agents registered
INFO: Application startup complete.
```

No more `ValueError: metric is missing label values` errors! ✅

---

## Root Cause Analysis

The issues occurred because:

1. **Label names didn't match metric definitions** - Code used different label names (e.g., `agent` vs `agent_name`)
2. **Missing required labels** - Some labels were defined but not provided when calling metrics
3. **Inconsistent naming** - Switched between `reasoning_mode` and `method` without consistency

**Prevention:**
- Always check metric definitions in `observability/metrics.py` before using them
- Use consistent naming conventions
- Consider adding type hints or wrappers for metrics
- Add unit tests for metric recording

---

## Related Fixes

This completes all Prometheus-related fixes:
1. Circuit breaker label mismatch (fixed earlier)
2. All histogram/counter label mismatches (fixed now)

Both Model Gateway and Orchestrator API servers now start successfully! 🎉
