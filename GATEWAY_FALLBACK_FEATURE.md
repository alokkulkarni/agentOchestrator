# Model Gateway Provider Fallback Feature

## Overview

The Model Gateway now supports **automatic provider fallback**, ensuring high availability and reliability. When a requested provider fails, the gateway automatically tries alternative providers transparently, with full observability through detailed logging.

## How It Works

### User Experience

When you specify a provider in your request:

```yaml
gateway:
  url: "http://localhost:8000"
  provider: "anthropic"  # Request Anthropic
```

**If Anthropic fails**, the gateway will:
1. ✅ Automatically try Bedrock (or next available provider)
2. ✅ Return successful response transparently
3. ✅ Log all fallback events for observability
4. ✅ User doesn't need to do anything - it just works!

### Architecture

```
Request Flow with Fallback:

User Request
   │
   ├─► Provider: "anthropic"
   │
   ▼
┌──────────────────────────────────────┐
│  Model Gateway                       │
│                                      │
│  1. Try Anthropic ────► ❌ Failed   │
│     (API Error)                      │
│                                      │
│  2. Fallback to Bedrock ──► ✅ OK   │
│     (Auto-retry)                     │
│                                      │
│  3. Return response from Bedrock    │
│     (Transparent to user)            │
└──────────────────────────────────────┘
   │
   ▼
Response to User
✅ Success (from Bedrock)
```

## Configuration

### Gateway Configuration (`model_gateway/config/gateway.yaml`)

```yaml
# Automatic Provider Fallback Configuration
fallback:
  # Enable automatic fallback between providers
  enabled: true

  # Order of providers to try on failure
  # Gateway will try providers in this sequence
  fallback_order:
    - "anthropic"
    - "bedrock"

  # Maximum number of fallback attempts
  # Should match number of providers
  max_fallback_attempts: 2

  # Retry original provider after successful fallback
  # Usually not needed - false recommended
  retry_original: false
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `true` | Enable/disable automatic fallback |
| `fallback_order` | list | `["anthropic", "bedrock"]` | Order of providers to try |
| `max_fallback_attempts` | integer | `2` | Maximum fallback attempts |
| `retry_original` | boolean | `false` | Retry original after fallback |

## Observability & Logging

### Fallback Event Logs

When fallback occurs, detailed logs are generated:

#### Warning Log (Provider Failure)
```
⚠️  Provider 'anthropic' failed (attempt 1/2): API connection timeout.
Trying fallback to 'bedrock'...
```

#### Success Log (Fallback Success)
```
🔄 FALLBACK SUCCESS: Provider 'bedrock' succeeded after 'anthropic' failed.
Attempt 2/2, latency=456.78ms
```

#### Request Log (Final Success)
```
Generated response: provider=BedrockProvider, model=claude-sonnet-3-5-v2-20241022,
tokens=28, latency=1250.45ms (fallback from anthropic)
```

### Log Symbols

- `⚠️` - Provider failure, attempting fallback
- `🔄` - Fallback successful, alternative provider used
- `❌` - All providers failed (rare)
- `✅` - Normal success without fallback

### Monitoring Fallback Events

#### Check Gateway Logs

```bash
# View real-time logs
tail -f model_gateway/gateway.log

# Search for fallback events
grep "FALLBACK" model_gateway/gateway.log

# Count fallback occurrences
grep -c "🔄 FALLBACK SUCCESS" model_gateway/gateway.log
```

#### Log Analysis

Fallback logs include:
- **Original provider requested**: e.g., "anthropic"
- **Provider that succeeded**: e.g., "bedrock"
- **Attempt number**: e.g., "2/2"
- **Latency**: Time for successful attempt
- **Error from failed provider**: Truncated error message
- **Total latency**: Including all attempts

## Scenarios & Examples

### Scenario 1: Anthropic API Key Invalid

**Configuration**:
```yaml
# Orchestrator requests Anthropic
gateway:
  provider: "anthropic"
```

**What Happens**:
1. Gateway tries Anthropic → Fails (invalid API key)
2. Gateway automatically tries Bedrock → Success
3. User receives response from Bedrock
4. Logs show fallback occurred

**User Impact**: None - request succeeds transparently

### Scenario 2: Anthropic Rate Limit Exceeded

**Configuration**:
```yaml
gateway:
  provider: "anthropic"
```

**What Happens**:
1. Gateway tries Anthropic → Fails (rate limit 429)
2. Gateway automatically tries Bedrock → Success
3. User gets response without waiting for rate limit

**User Impact**: None - no rate limit experienced

### Scenario 3: AWS Credentials Not Configured

**Configuration**:
```yaml
gateway:
  provider: "bedrock"
```

**What Happens**:
1. Gateway tries Bedrock → Fails (no AWS credentials)
2. Gateway automatically tries Anthropic → Success
3. User receives response from Anthropic

**User Impact**: None - seamless fallback

### Scenario 4: All Providers Fail

**Configuration**:
```yaml
gateway:
  provider: "anthropic"
```

**What Happens**:
1. Gateway tries Anthropic → Fails
2. Gateway tries Bedrock → Fails
3. Gateway returns error with details of all attempts

**Response**:
```json
{
  "detail": {
    "message": "All providers failed",
    "requested_provider": "anthropic",
    "attempts": [
      {
        "provider": "anthropic",
        "attempt": 1,
        "error": "Invalid API key",
        "latency_ms": 125.5
      },
      {
        "provider": "bedrock",
        "attempt": 2,
        "error": "No AWS credentials found",
        "latency_ms": 89.2
      }
    ],
    "total_latency_ms": 214.7,
    "last_error": "No AWS credentials found"
  }
}
```

## Testing Fallback

### Test Setup

To test fallback, you need to simulate a provider failure.

#### Option 1: Invalid API Key

```bash
# Set invalid Anthropic API key
export GATEWAY_ANTHROPIC_API_KEY="invalid-key-for-testing"

# Start gateway
python3 -m model_gateway.server
```

Now requests to Anthropic will fail and fallback to Bedrock.

#### Option 2: Disable Provider in Config

```yaml
# In model_gateway/config/gateway.yaml
providers:
  anthropic:
    type: "anthropic"
    enabled: false  # Disable Anthropic
```

### Run Fallback Tests

```bash
# Run fallback test script
python3 test_gateway_fallback.py
```

### Manual Testing

```bash
# Request with Anthropic (will fallback to Bedrock if Anthropic fails)
curl -X POST http://localhost:8000/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What is 25 + 75?"}],
    "provider": "anthropic",
    "max_tokens": 50
  }' | python3 -m json.tool

# Check logs for fallback
tail -20 model_gateway/gateway.log | grep -E "⚠️|🔄"
```

## Performance Impact

### Latency Considerations

**Normal Request (no fallback)**:
- Single provider attempt
- Latency: ~500-2000ms (typical AI API call)

**Fallback Request**:
- Failed attempt latency: ~100-500ms (timeout/error)
- Successful fallback latency: ~500-2000ms (AI API call)
- **Total latency**: ~600-2500ms

**Impact**: Additional 100-500ms for failed attempt, but request succeeds instead of failing.

### Optimization Tips

1. **Order providers by reliability**:
   ```yaml
   fallback_order:
     - "anthropic"  # Most reliable first
     - "bedrock"    # Fallback second
   ```

2. **Set appropriate timeouts**:
   ```yaml
   providers:
     anthropic:
       timeout: 30  # Don't wait too long
   ```

3. **Monitor fallback frequency**:
   ```bash
   # If seeing many fallbacks, investigate primary provider
   grep -c "FALLBACK SUCCESS" model_gateway/gateway.log
   ```

## Disabling Fallback

If you want to disable automatic fallback:

```yaml
# In model_gateway/config/gateway.yaml
fallback:
  enabled: false
```

With fallback disabled:
- Only requested provider is tried
- Failures return immediately
- No automatic retry
- Useful for debugging specific provider issues

## Advanced Configuration

### Custom Fallback Order Per Request

Currently, fallback order is global. Future enhancement could support per-request fallback:

```json
{
  "messages": [...],
  "provider": "anthropic",
  "fallback_providers": ["bedrock", "anthropic"]  // Custom order
}
```

### Provider-Specific Fallback Rules

Future enhancement for conditional fallback:

```yaml
fallback:
  rules:
    - if_provider: "anthropic"
      on_error: "rate_limit"
      fallback_to: "bedrock"

    - if_provider: "bedrock"
      on_error: "validation_error"
      fallback_to: "anthropic"
```

## Best Practices

### 1. Always Enable Fallback in Production
```yaml
fallback:
  enabled: true  # Production recommended
```

### 2. Monitor Fallback Frequency
```bash
# Daily fallback count
grep "FALLBACK SUCCESS" model_gateway/gateway.log | \
  grep "$(date +%Y-%m-%d)" | wc -l
```

### 3. Alert on High Fallback Rate
```bash
# If fallbacks > 10% of requests, investigate primary provider
```

### 4. Configure Both Providers
- Ensure both Anthropic AND Bedrock are properly configured
- Test both providers independently
- Verify credentials for both

### 5. Set Appropriate Timeouts
```yaml
providers:
  anthropic:
    timeout: 30  # Fail fast, don't block fallback
```

### 6. Log Analysis
```bash
# Weekly fallback report
grep "FALLBACK SUCCESS" model_gateway/gateway.log | \
  awk -F"'" '{print $2}' | sort | uniq -c
```

## Troubleshooting

### Issue: Fallback Not Happening

**Check**:
1. Fallback enabled in config?
   ```yaml
   fallback:
     enabled: true
   ```

2. Multiple providers configured and enabled?
   ```yaml
   providers:
     anthropic:
       enabled: true
     bedrock:
       enabled: true
   ```

3. Gateway logs show provider failure?
   ```bash
   grep "failed" model_gateway/gateway.log
   ```

### Issue: All Providers Failing

**Check**:
1. Anthropic API key valid?
2. AWS credentials configured?
3. Network connectivity?
4. Provider service status?

### Issue: Unexpected Provider Used

**Check logs**:
```bash
# See which provider was actually used
grep "Generated response" model_gateway/gateway.log | tail -5
```

**Check config**:
```yaml
fallback_order:
  - "anthropic"  # This should be tried first
  - "bedrock"    # This is fallback
```

## Summary

### Key Benefits

✅ **High Availability**: Service continues even if one provider fails
✅ **Transparent**: Users don't need to handle provider failures
✅ **Observable**: Complete visibility into fallback events
✅ **Configurable**: Control fallback behavior per deployment
✅ **Fast**: Fails fast and tries alternative quickly

### Implementation Files

- `model_gateway/config/models.py` - FallbackConfig model
- `model_gateway/config/gateway.yaml` - Fallback configuration
- `model_gateway/server.py` - Fallback logic implementation
- `test_gateway_fallback.py` - Fallback tests

### Next Steps

1. ✅ Configure fallback in `gateway.yaml`
2. ✅ Start gateway with fallback enabled
3. ✅ Monitor logs for fallback events
4. ✅ Set up alerting for high fallback rates
5. ✅ Test fallback behavior in staging

---

**The Model Gateway now provides enterprise-grade reliability with automatic provider fallback!** 🎉
