# Action Evaluators - Policy and Constraint System

## Overview

The **Action Evaluator** system provides intelligent policy enforcement and constraint validation for the orchestrator. It tracks all user interactions and evaluates whether requested actions are allowed based on configurable rules, timing restrictions, rate limits, and value thresholds.

### Key Features

- ✅ **User Action History Tracking** - Complete history of all user actions
- ✅ **Policy-Based Evaluation** - Configurable rules for action validation
- ✅ **Time-Based Restrictions** - Block actions for a period after trigger events
- ✅ **Rate Limiting** - Limit frequency of sensitive actions
- ✅ **Threshold Validation** - Validate values against configured limits
- ✅ **Graceful Denial** - User-friendly denial messages with conversational tone
- ✅ **Multi-Agent Support** - Works with single, parallel, and sequential agent requests
- ✅ **Extensible** - Easy to add custom evaluators

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                            │
│             {"query": "order a new card", "user_id": "user123"} │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR                                │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  1. Security Validation                                │    │
│  │  2. Agent Selection (Reasoning)                        │    │
│  └────────────────────────────────────────────────────────┘    │
│                         │                                       │
│                         ▼                                       │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  3. 🆕 ACTION EVALUATION (Policy Check)                │    │
│  │                                                        │    │
│  │  • Map query to action category                       │    │
│  │  • Check user action history                          │    │
│  │  • Run all configured evaluators                      │    │
│  │  • Deny or allow action                               │    │
│  └────────────────────────────────────────────────────────┘    │
│                         │                                       │
│           ┌─────────────┴──────────────┐                       │
│           │                            │                       │
│           ▼                            ▼                       │
│     ┌──────────┐               ┌──────────────┐               │
│     │ DENIED   │               │   ALLOWED    │               │
│     │          │               │              │               │
│     │ Return   │               │ 4. Execute   │               │
│     │ graceful │               │    agents    │               │
│     │ message  │               │              │               │
│     └──────────┘               │ 5. Record    │               │
│                                │    action in │               │
│                                │    history   │               │
│                                └──────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

## Action Categories

Actions are classified into categories for policy evaluation:

| Category | Description | Examples |
|----------|-------------|----------|
| `address_change` | User changes their address | "Update my address to..." |
| `payment_method_change` | Changes to payment methods | "Add a new credit card" |
| `password_change` | Password updates | "Change my password" |
| `card_order` | Ordering new cards | "Order a replacement card" |
| `high_value_transaction` | Large financial transactions | "Transfer $10,000" |
| `transfer` | Money transfers | "Send money to..." |
| `purchase` | Purchases | "Buy product X" |
| `account_closure` | Account closure requests | "Close my account" |
| `query` | Information queries only | "What is my balance?" |
| `other` | Uncategorized actions | - |

## Built-in Evaluators

### 1. Timed Restriction Evaluator

Blocks certain actions for a time period after a trigger action.

**Use Case**: After an address change, prevent high-risk actions like ordering cards or making large transactions.

**Configuration**:
```yaml
- name: address_change_restriction
  type: timed_restriction
  enabled: true
  config:
    restrictions:
      - trigger_category: address_change
        blocked_categories:
          - card_order
          - high_value_transaction
        block_hours: 24
        reason: "For your security, this action is temporarily restricted after an address change"
```

**How It Works**:
1. Checks if user performed trigger action (e.g., address_change) recently
2. If yes, checks if requested action is in blocked categories
3. If blocked, calculates time remaining and denies request
4. Provides clear message with unblock time

### 2. Rate Limit Evaluator

Limits the frequency of certain actions within a time window.

**Use Case**: Limit high-value transactions to 3 per day for fraud prevention.

**Configuration**:
```yaml
- name: transaction_rate_limit
  type: rate_limit
  enabled: true
  config:
    limits:
      - category: high_value_transaction
        max_count: 3
        window_hours: 24
        reason: "Daily high-value transaction limit reached for your security"
```

**How It Works**:
1. Counts how many times user performed this action in the time window
2. If count >= max_count, denies request
3. Calculates when the limit will reset
4. Provides message with current count and limit

### 3. Threshold Evaluator

Validates values against configured maximum thresholds.

**Use Case**: Prevent transactions over $10,000 without additional verification.

**Configuration**:
```yaml
- name: transaction_threshold
  type: threshold
  enabled: true
  config:
    thresholds:
      - category: high_value_transaction
        field: amount
        max_value: 10000
        reason: "Transaction amount exceeds the allowed limit"
```

**How It Works**:
1. Extracts value from request details (e.g., `amount` field)
2. Compares against configured max_value
3. If exceeded, denies request with current and max values

## Configuration

### Evaluators Configuration File

Create `config/evaluators.yaml`:

```yaml
# List of evaluators
evaluators:
  # Evaluator 1
  - name: my_evaluator
    type: timed_restriction  # or rate_limit, threshold
    enabled: true
    config:
      # Evaluator-specific configuration
      ...

  # Evaluator 2
  - name: another_evaluator
    type: rate_limit
    enabled: false  # Can be disabled
    config:
      ...

# Global settings
settings:
  max_history_days: 90
  max_actions_per_user: 1000
  enable_auto_cleanup: true
  cleanup_interval_hours: 24
```

### Complete Example

See `config/evaluators.yaml` for a complete working example with:
- Address change restrictions (24 hour blocks)
- Transaction rate limits (3 per day)
- Card order limits (5 per month)
- Value thresholds ($10,000 limit)

## User Identification

The evaluator system requires a `user_id` to track actions. Provide it in requests:

```python
result = await orchestrator.process({
    "query": "order a new card",
    "user_id": "user123",  # Required for evaluators
    # ... other fields
})
```

If `user_id` is not provided, the system falls back to `session_id` or "anonymous".

## Creating Custom Evaluators

### Step 1: Create Evaluator Class

Create a new class that inherits from `ActionEvaluator`:

```python
from agent_orchestrator.evaluators import ActionEvaluator, EvaluationResult, ActionCategory

class CustomEvaluator(ActionEvaluator):
    """My custom evaluator logic."""
    
    async def evaluate(
        self,
        user_id: str,
        requested_action: str,
        requested_category: ActionCategory,
        action_history: UserActionHistory,
        request_details: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        # Your custom logic here
        
        # Check some condition
        if some_condition:
            return EvaluationResult(
                allowed=False,
                reason="Action not allowed because...",
                evaluator_name=self.name,
                metadata={"extra": "info"}
            )
        
        # Allow action
        return EvaluationResult(allowed=True)
```

### Step 2: Register Custom Evaluator

```python
from agent_orchestrator.evaluators.registry import EvaluatorRegistry

# Register your custom type
EvaluatorRegistry.register_custom_evaluator_type(
    "custom",  # Type name for config
    CustomEvaluator  # Your class
)
```

### Step 3: Add to Configuration

```yaml
evaluators:
  - name: my_custom_evaluator
    type: custom  # Your registered type
    enabled: true
    config:
      # Your custom config
      custom_setting: value
```

## Denial Messages

When an action is denied, users receive:

1. **Clear Reason**: Why the action was denied
2. **Time Information**: When the restriction will be lifted (if applicable)
3. **Conversational Tone**: Friendly, helpful message
4. **Follow-up Prompt**: What they can do next

**Example Denial**:
```
🚫 For your security, this action is temporarily restricted after an address change. 
Please wait 22.5 more hours (since address_change on 2026-01-26 15:30:00)

⏰ This restriction will be lifted on 2026-01-27 at 15:30:00.

────────────────────────────────────────────────────────────
💬 I'm here to help. What else can I assist you with?
```

## Action History Tracking

### What Is Tracked

For each action, the system records:
- User ID
- Action type (user's query)
- Action category
- Timestamp
- Agent name that handled it
- Success/failure status
- Additional details
- Metadata

### Querying History

```python
# Get recent actions for a user
actions = action_history.get_user_actions(
    user_id="user123",
    categories=[ActionCategory.ADDRESS_CHANGE],
    since_hours=24,
    limit=10
)

# Check if user has recent action
has_recent = action_history.has_recent_action(
    user_id="user123",
    action_category=ActionCategory.ADDRESS_CHANGE,
    within_hours=24
)

# Get last action
last_action = action_history.get_last_action(
    user_id="user123",
    action_category=ActionCategory.CARD_ORDER
)

# Count actions
count = action_history.count_actions(
    user_id="user123",
    action_category=ActionCategory.TRANSFER,
    since_hours=24
)
```

### Cleanup

Old actions are automatically cleaned up based on configuration:
- `max_history_days`: Actions older than this are removed
- `max_actions_per_user`: Keeps only the N most recent actions per user

## Integration Examples

### Example 1: Address Change Scenario

```python
# User changes address
result1 = await orchestrator.process({
    "query": "change my address to 123 Main St",
    "user_id": "user123"
})
# ✅ Allowed - Address changed successfully
# Action recorded in history

# Immediately try to order card
result2 = await orchestrator.process({
    "query": "order a new debit card",
    "user_id": "user123"
})
# ❌ Denied - "For your security, this action is temporarily restricted 
#             after an address change. Please wait 24 more hours..."
```

### Example 2: Rate Limit Scenario

```python
# User makes 3 high-value transactions (allowed)
for i in range(3):
    result = await orchestrator.process({
        "query": f"transfer $9000 transaction {i+1}",
        "user_id": "user123",
        "amount": 9000
    })
    # ✅ All allowed

# Try 4th transaction
result4 = await orchestrator.process({
    "query": "transfer $9000 transaction 4",
    "user_id": "user123",
    "amount": 9000
})
# ❌ Denied - "Daily high-value transaction limit reached for your security. 
#             You have performed 3 high_value_transaction action(s) in the 
#             last 24 hours. Maximum allowed: 3."
```

### Example 3: Threshold Scenario

```python
# Try transfer over limit
result = await orchestrator.process({
    "query": "transfer $15000",
    "user_id": "user123",
    "amount": 15000
})
# ❌ Denied - "Transaction amount exceeds the allowed limit. 
#             Provided amount: 15000, Maximum allowed: 10000."
```

## Testing

### Check Evaluator Stats

```python
stats = orchestrator.get_stats()
print(stats["evaluators"])
# Output:
# {
#     "total_evaluators": 3,
#     "enabled_evaluators": 3,
#     "evaluator_names": ["address_change_restriction", "transaction_rate_limit", "transaction_threshold"]
# }
```

### Check Action History Stats

```python
print(stats["action_history"])
# Output:
# {
#     "total_users": 5,
#     "total_actions": 42,
#     "avg_actions_per_user": 8.4
# }
```

## Best Practices

### 1. Use Appropriate Categories

Map actions to the most specific category:
```python
# Good
action_category = ActionCategory.ADDRESS_CHANGE

# Avoid
action_category = ActionCategory.OTHER
```

### 2. Set Reasonable Time Windows

Consider user experience:
```yaml
# Too restrictive (1 year!)
block_hours: 8760

# Better (24 hours)
block_hours: 24
```

### 3. Provide Clear Reasons

```yaml
# Good
reason: "For your security, this action is temporarily restricted after an address change"

# Avoid
reason: "Not allowed"
```

### 4. Test Evaluators Thoroughly

Before deploying:
1. Test with various user scenarios
2. Verify time calculations
3. Check edge cases (exactly at limit, etc.)
4. Ensure messages are user-friendly

### 5. Monitor Action History

Regularly check:
- Total users and actions
- History growth rate
- Cleanup effectiveness
- Common denied actions

## Troubleshooting

### Issue: Actions Not Being Denied

**Check**:
1. Is evaluator enabled in config?
2. Is action category mapped correctly?
3. Are time windows correct?
4. Check logs for evaluation results

### Issue: Wrong Denial Reasons

**Check**:
1. Review evaluator configuration
2. Verify action category mapping
3. Check request_details extraction

### Issue: History Growing Too Large

**Solutions**:
1. Reduce `max_history_days`
2. Reduce `max_actions_per_user`
3. Enable auto-cleanup
4. Manually trigger cleanup:
```python
action_history.cleanup_old_actions()
```

## Performance Considerations

The evaluator system is designed for minimal overhead:

- **Action History Lookup**: O(n) where n = actions for user (typically < 1000)
- **Evaluation**: O(m) where m = number of evaluators (typically < 10)
- **Memory**: ~1-2 KB per user with history
- **No External Dependencies**: Everything in-memory
- **No Database Queries**: Fast, synchronous evaluation

## Security Considerations

### Data Privacy

- Action history is stored in-memory only (not persisted)
- Sensitive data should not be included in action details
- Consider GDPR/privacy requirements for action retention

### Denial of Service

- Rate limiters protect against abuse
- Max actions per user prevents memory exhaustion
- Auto-cleanup prevents unbounded growth

### Bypassing Evaluators

- Evaluators run before agent execution
- No way to bypass via parameters
- Disabled evaluators are completely skipped

## Extensibility

The evaluator system is designed to be extended:

1. **Custom Evaluators** - Create your own logic
2. **Custom Categories** - Add new ActionCategory values
3. **Custom Queries** - Enhance `map_query_to_action_category()`
4. **Custom Metadata** - Add fields to UserAction
5. **Custom Storage** - Replace in-memory with persistent storage

## Future Enhancements

Potential improvements:
- Machine learning-based anomaly detection
- User risk scoring
- Dynamic threshold adjustment
- Integration with external fraud detection services
- Persistent action history (database)
- Real-time notifications for denied actions
- Admin dashboard for policy management

## Summary

The Action Evaluator system provides:

✅ **Protection** - Prevent risky actions based on recent user behavior
✅ **Flexibility** - Configurable rules without code changes
✅ **User Experience** - Clear, helpful denial messages
✅ **Extensibility** - Easy to add custom evaluators
✅ **Performance** - Minimal overhead, in-memory operation
✅ **Transparency** - Full audit trail of user actions

Use it to implement sophisticated business policies, fraud prevention, compliance requirements, and user protection measures in your orchestrator-based applications!
