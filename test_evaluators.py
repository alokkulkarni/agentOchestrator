#!/usr/bin/env python3
"""
Test script for the evaluator system.

Demonstrates:
1. Address change restrictions
2. Rate limiting
3. Threshold validation
4. Graceful denial messages
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_orchestrator.evaluators import (
    ActionCategory,
    UserActionHistory,
    TimedRestrictionEvaluator,
    RateLimitEvaluator,
    ThresholdEvaluator,
)


async def test_timed_restriction():
    """Test timed restriction evaluator."""
    print("=" * 80)
    print("TEST 1: Timed Restriction Evaluator")
    print("=" * 80)
    print()
    
    history = UserActionHistory()
    
    evaluator = TimedRestrictionEvaluator(
        name="test_restriction",
        config={
            "restrictions": [
                {
                    "trigger_category": "address_change",
                    "blocked_categories": ["card_order", "high_value_transaction"],
                    "block_hours": 24,
                    "reason": "Action temporarily restricted after address change"
                }
            ]
        }
    )
    
    # Simulate address change
    print("1. User changes address...")
    history.record_action(
        user_id="user123",
        action_type="change_address",
        action_category=ActionCategory.ADDRESS_CHANGE
    )
    print("✅ Address change recorded\n")
    
    # Try to order card immediately
    print("2. User tries to order card immediately...")
    result = await evaluator.evaluate(
        user_id="user123",
        requested_action="order_card",
        requested_category=ActionCategory.CARD_ORDER,
        action_history=history
    )
    
    if result.allowed:
        print("✅ ALLOWED")
    else:
        print(f"❌ DENIED: {result.reason}")
        if result.blocked_until:
            print(f"   Blocked until: {result.blocked_until}")
    print()


async def test_rate_limit():
    """Test rate limit evaluator."""
    print("=" * 80)
    print("TEST 2: Rate Limit Evaluator")
    print("=" * 80)
    print()
    
    history = UserActionHistory()
    
    evaluator = RateLimitEvaluator(
        name="test_rate_limit",
        config={
            "limits": [
                {
                    "category": "high_value_transaction",
                    "max_count": 3,
                    "window_hours": 24,
                    "reason": "Daily transaction limit reached"
                }
            ]
        }
    )
    
    # Make 3 transactions (allowed)
    print("1. User makes 3 high-value transactions...")
    for i in range(3):
        history.record_action(
            user_id="user456",
            action_type=f"transaction_{i+1}",
            action_category=ActionCategory.HIGH_VALUE_TRANSACTION
        )
        print(f"   ✅ Transaction {i+1} recorded")
    print()
    
    # Try 4th transaction
    print("2. User tries 4th transaction...")
    result = await evaluator.evaluate(
        user_id="user456",
        requested_action="transaction_4",
        requested_category=ActionCategory.HIGH_VALUE_TRANSACTION,
        action_history=history
    )
    
    if result.allowed:
        print("✅ ALLOWED")
    else:
        print(f"❌ DENIED: {result.reason}")
        if result.metadata:
            print(f"   Current count: {result.metadata.get('current_count')}")
            print(f"   Max count: {result.metadata.get('max_count')}")
    print()


async def test_threshold():
    """Test threshold evaluator."""
    print("=" * 80)
    print("TEST 3: Threshold Evaluator")
    print("=" * 80)
    print()
    
    history = UserActionHistory()
    
    evaluator = ThresholdEvaluator(
        name="test_threshold",
        config={
            "thresholds": [
                {
                    "category": "high_value_transaction",
                    "field": "amount",
                    "max_value": 10000,
                    "reason": "Transaction amount exceeds limit"
                }
            ]
        }
    )
    
    # Try transaction under limit
    print("1. User tries $5,000 transaction (under limit)...")
    result = await evaluator.evaluate(
        user_id="user789",
        requested_action="transfer_5000",
        requested_category=ActionCategory.HIGH_VALUE_TRANSACTION,
        action_history=history,
        request_details={"amount": 5000}
    )
    
    if result.allowed:
        print("✅ ALLOWED")
    else:
        print(f"❌ DENIED: {result.reason}")
    print()
    
    # Try transaction over limit
    print("2. User tries $15,000 transaction (over limit)...")
    result = await evaluator.evaluate(
        user_id="user789",
        requested_action="transfer_15000",
        requested_category=ActionCategory.HIGH_VALUE_TRANSACTION,
        action_history=history,
        request_details={"amount": 15000}
    )
    
    if result.allowed:
        print("✅ ALLOWED")
    else:
        print(f"❌ DENIED: {result.reason}")
        if result.metadata:
            print(f"   Requested: ${result.metadata.get('value')}")
            print(f"   Maximum: ${result.metadata.get('max_value')}")
    print()


async def test_action_history():
    """Test action history queries."""
    print("=" * 80)
    print("TEST 4: Action History Queries")
    print("=" * 80)
    print()
    
    history = UserActionHistory()
    
    # Record multiple actions
    print("1. Recording sample actions...")
    actions_data = [
        ("user_a", "query_balance", ActionCategory.QUERY),
        ("user_a", "transfer_100", ActionCategory.TRANSFER),
        ("user_a", "change_address", ActionCategory.ADDRESS_CHANGE),
        ("user_b", "order_card", ActionCategory.CARD_ORDER),
        ("user_b", "transfer_5000", ActionCategory.HIGH_VALUE_TRANSACTION),
    ]
    
    for user_id, action_type, category in actions_data:
        history.record_action(user_id, action_type, category)
        print(f"   ✅ {user_id}: {action_type}")
    print()
    
    # Query history
    print("2. Querying action history...")
    
    # All actions for user_a
    user_a_actions = history.get_user_actions("user_a")
    print(f"   User A total actions: {len(user_a_actions)}")
    
    # Recent address changes for user_a
    address_changes = history.get_user_actions(
        "user_a",
        categories=[ActionCategory.ADDRESS_CHANGE]
    )
    print(f"   User A address changes: {len(address_changes)}")
    
    # Check for recent action
    has_recent = history.has_recent_action(
        "user_a",
        ActionCategory.ADDRESS_CHANGE,
        within_hours=1
    )
    print(f"   User A has recent address change: {has_recent}")
    
    # Count transfers
    transfer_count = history.count_actions(
        "user_a",
        ActionCategory.TRANSFER
    )
    print(f"   User A transfers: {transfer_count}")
    print()
    
    # Stats
    print("3. History statistics...")
    stats = history.get_stats()
    print(f"   Total users: {stats['total_users']}")
    print(f"   Total actions: {stats['total_actions']}")
    print(f"   Avg actions/user: {stats['avg_actions_per_user']:.1f}")
    print()


async def main():
    """Run all tests."""
    print("\n🧪 Evaluator System Tests\n")
    
    try:
        await test_timed_restriction()
        await test_rate_limit()
        await test_threshold()
        await test_action_history()
        
        print("=" * 80)
        print("✅ All tests completed successfully!")
        print("=" * 80)
        print()
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
