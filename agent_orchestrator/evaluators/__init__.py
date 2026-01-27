"""
User action history tracking and policy evaluation framework.

This module provides:
- User action history tracking across sessions
- Policy evaluators to validate if actions are allowed
- Configurable rules-based and time-based restrictions
- Integration with orchestrator for pre-execution validation
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from enum import Enum

logger = logging.getLogger(__name__)


class ActionCategory(Enum):
    """Categories of user actions for policy evaluation."""
    PROFILE_CHANGE = "profile_change"
    ADDRESS_CHANGE = "address_change"
    PAYMENT_METHOD_CHANGE = "payment_method_change"
    HIGH_VALUE_TRANSACTION = "high_value_transaction"
    CARD_ORDER = "card_order"
    ACCOUNT_CLOSURE = "account_closure"
    PASSWORD_CHANGE = "password_change"
    TRANSFER = "transfer"
    PURCHASE = "purchase"
    QUERY = "query"
    OTHER = "other"


@dataclass
class UserAction:
    """Represents a single user action with metadata."""
    user_id: str
    action_type: str
    action_category: ActionCategory
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    agent_name: Optional[str] = None
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def age_seconds(self) -> float:
        """Get age of this action in seconds."""
        return (datetime.utcnow() - self.timestamp).total_seconds()
    
    def age_minutes(self) -> float:
        """Get age of this action in minutes."""
        return self.age_seconds() / 60
    
    def age_hours(self) -> float:
        """Get age of this action in hours."""
        return self.age_seconds() / 3600
    
    def age_days(self) -> float:
        """Get age of this action in days."""
        return self.age_seconds() / 86400


class UserActionHistory:
    """
    Tracks all user actions with efficient querying capabilities.
    
    Features:
    - Per-user action history
    - Time-based queries
    - Action category filtering
    - Automatic cleanup of old actions
    """
    
    def __init__(self, max_history_per_user: int = 1000, max_age_days: int = 90):
        """
        Initialize user action history tracker.
        
        Args:
            max_history_per_user: Maximum actions to keep per user
            max_age_days: Maximum age of actions to keep
        """
        self.max_history_per_user = max_history_per_user
        self.max_age_days = max_age_days
        self._history: Dict[str, List[UserAction]] = {}
        
    def record_action(
        self,
        user_id: str,
        action_type: str,
        action_category: ActionCategory,
        details: Optional[Dict[str, Any]] = None,
        agent_name: Optional[str] = None,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UserAction:
        """
        Record a user action.
        
        Args:
            user_id: User identifier
            action_type: Type of action (e.g., "change_address", "order_card")
            action_category: Category from ActionCategory enum
            details: Additional action details
            agent_name: Name of agent that handled this action
            success: Whether action was successful
            metadata: Additional metadata
            
        Returns:
            The created UserAction
        """
        action = UserAction(
            user_id=user_id,
            action_type=action_type,
            action_category=action_category,
            timestamp=datetime.utcnow(),
            details=details or {},
            agent_name=agent_name,
            success=success,
            metadata=metadata or {}
        )
        
        # Add to history
        if user_id not in self._history:
            self._history[user_id] = []
        
        self._history[user_id].append(action)
        
        # Trim if needed
        if len(self._history[user_id]) > self.max_history_per_user:
            self._history[user_id] = self._history[user_id][-self.max_history_per_user:]
        
        logger.debug(
            f"Recorded action for user {user_id}: {action_type} "
            f"(category: {action_category.value})"
        )
        
        return action
    
    def get_user_actions(
        self,
        user_id: str,
        categories: Optional[List[ActionCategory]] = None,
        since_hours: Optional[float] = None,
        limit: Optional[int] = None,
        success_only: bool = False
    ) -> List[UserAction]:
        """
        Get user actions with optional filtering.
        
        Args:
            user_id: User identifier
            categories: Filter by action categories
            since_hours: Only return actions within last N hours
            limit: Maximum number of actions to return
            success_only: Only return successful actions
            
        Returns:
            List of UserAction objects matching criteria
        """
        if user_id not in self._history:
            return []
        
        actions = self._history[user_id]
        
        # Filter by time
        if since_hours is not None:
            cutoff_time = datetime.utcnow() - timedelta(hours=since_hours)
            actions = [a for a in actions if a.timestamp >= cutoff_time]
        
        # Filter by category
        if categories:
            actions = [a for a in actions if a.action_category in categories]
        
        # Filter by success
        if success_only:
            actions = [a for a in actions if a.success]
        
        # Sort by timestamp (newest first)
        actions = sorted(actions, key=lambda a: a.timestamp, reverse=True)
        
        # Apply limit
        if limit:
            actions = actions[:limit]
        
        return actions
    
    def has_recent_action(
        self,
        user_id: str,
        action_category: ActionCategory,
        within_hours: float
    ) -> bool:
        """
        Check if user has performed an action of given category recently.
        
        Args:
            user_id: User identifier
            action_category: Action category to check
            within_hours: Time window in hours
            
        Returns:
            True if user has recent action in this category
        """
        actions = self.get_user_actions(
            user_id=user_id,
            categories=[action_category],
            since_hours=within_hours,
            success_only=True
        )
        return len(actions) > 0
    
    def get_last_action(
        self,
        user_id: str,
        action_category: Optional[ActionCategory] = None
    ) -> Optional[UserAction]:
        """
        Get the most recent action for a user.
        
        Args:
            user_id: User identifier
            action_category: Optional category filter
            
        Returns:
            Most recent UserAction or None
        """
        categories = [action_category] if action_category else None
        actions = self.get_user_actions(
            user_id=user_id,
            categories=categories,
            limit=1,
            success_only=True
        )
        return actions[0] if actions else None
    
    def count_actions(
        self,
        user_id: str,
        action_category: Optional[ActionCategory] = None,
        since_hours: Optional[float] = None
    ) -> int:
        """
        Count actions for a user with optional filtering.
        
        Args:
            user_id: User identifier
            action_category: Optional category filter
            since_hours: Optional time window
            
        Returns:
            Count of matching actions
        """
        categories = [action_category] if action_category else None
        actions = self.get_user_actions(
            user_id=user_id,
            categories=categories,
            since_hours=since_hours,
            success_only=True
        )
        return len(actions)
    
    def cleanup_old_actions(self):
        """Remove actions older than max_age_days."""
        cutoff_time = datetime.utcnow() - timedelta(days=self.max_age_days)
        
        for user_id in list(self._history.keys()):
            original_count = len(self._history[user_id])
            self._history[user_id] = [
                a for a in self._history[user_id]
                if a.timestamp >= cutoff_time
            ]
            removed = original_count - len(self._history[user_id])
            
            if removed > 0:
                logger.info(f"Cleaned up {removed} old actions for user {user_id}")
            
            # Remove user if no actions remain
            if not self._history[user_id]:
                del self._history[user_id]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about tracked actions."""
        total_users = len(self._history)
        total_actions = sum(len(actions) for actions in self._history.values())
        
        return {
            "total_users": total_users,
            "total_actions": total_actions,
            "avg_actions_per_user": total_actions / total_users if total_users > 0 else 0
        }


@dataclass
class EvaluationResult:
    """Result of an action evaluation."""
    allowed: bool
    reason: Optional[str] = None
    evaluator_name: Optional[str] = None
    blocked_until: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "allowed": self.allowed,
            "reason": self.reason,
            "evaluator_name": self.evaluator_name,
        }
        if self.blocked_until:
            result["blocked_until"] = self.blocked_until.isoformat()
        if self.metadata:
            result["metadata"] = self.metadata
        return result


class ActionEvaluator(ABC):
    """
    Base class for action evaluators.
    
    Evaluators check if a requested action is allowed based on
    user history, timing rules, or other policies.
    """
    
    def __init__(self, name: str, enabled: bool = True, config: Optional[Dict[str, Any]] = None):
        """
        Initialize evaluator.
        
        Args:
            name: Evaluator name
            enabled: Whether this evaluator is active
            config: Evaluator-specific configuration
        """
        self.name = name
        self.enabled = enabled
        self.config = config or {}
    
    @abstractmethod
    async def evaluate(
        self,
        user_id: str,
        requested_action: str,
        requested_category: ActionCategory,
        action_history: UserActionHistory,
        request_details: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        """
        Evaluate if the requested action is allowed.
        
        Args:
            user_id: User requesting the action
            requested_action: Action type being requested
            requested_category: Category of requested action
            action_history: User's action history
            request_details: Additional request details
            
        Returns:
            EvaluationResult indicating if action is allowed
        """
        pass
    
    def _extract_value(self, request_details: Dict[str, Any], key: str, default: Any = None) -> Any:
        """Helper to extract values from request details."""
        return request_details.get(key, default) if request_details else default


class TimedRestrictionEvaluator(ActionEvaluator):
    """
    Evaluator that restricts actions for a time period after another action.
    
    Example: Cannot order card for 24 hours after address change.
    """
    
    def __init__(self, name: str, enabled: bool = True, config: Optional[Dict[str, Any]] = None):
        """
        Initialize timed restriction evaluator.
        
        Config format:
        {
            "restrictions": [
                {
                    "trigger_category": "address_change",
                    "blocked_categories": ["card_order", "high_value_transaction"],
                    "block_hours": 24,
                    "reason": "Cannot perform this action immediately after address change"
                }
            ]
        }
        """
        super().__init__(name, enabled, config)
        self.restrictions = self.config.get("restrictions", [])
    
    async def evaluate(
        self,
        user_id: str,
        requested_action: str,
        requested_category: ActionCategory,
        action_history: UserActionHistory,
        request_details: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        """Evaluate based on timed restrictions."""
        if not self.enabled:
            return EvaluationResult(allowed=True)
        
        # Check each restriction
        for restriction in self.restrictions:
            trigger_cat_str = restriction.get("trigger_category")
            trigger_category = ActionCategory(trigger_cat_str)
            
            blocked_cats_str = restriction.get("blocked_categories", [])
            blocked_categories = [ActionCategory(cat) for cat in blocked_cats_str]
            
            block_hours = restriction.get("block_hours", 24)
            reason_template = restriction.get("reason", "Action temporarily blocked")
            
            # Check if requested action is in blocked list
            if requested_category not in blocked_categories:
                continue
            
            # Check if user has recent trigger action
            last_trigger = action_history.get_last_action(user_id, trigger_category)
            
            if last_trigger and last_trigger.age_hours() < block_hours:
                hours_remaining = block_hours - last_trigger.age_hours()
                blocked_until = last_trigger.timestamp + timedelta(hours=block_hours)
                
                reason = (
                    f"{reason_template}. "
                    f"Please wait {hours_remaining:.1f} more hours "
                    f"(since {trigger_category.value} on {last_trigger.timestamp.strftime('%Y-%m-%d %H:%M:%S')})"
                )
                
                return EvaluationResult(
                    allowed=False,
                    reason=reason,
                    evaluator_name=self.name,
                    blocked_until=blocked_until,
                    metadata={
                        "trigger_action": trigger_category.value,
                        "trigger_timestamp": last_trigger.timestamp.isoformat(),
                        "hours_remaining": hours_remaining
                    }
                )
        
        # No restrictions triggered
        return EvaluationResult(allowed=True)


class RateLimitEvaluator(ActionEvaluator):
    """
    Evaluator that limits rate of certain actions.
    
    Example: Maximum 3 high-value transactions per day.
    """
    
    def __init__(self, name: str, enabled: bool = True, config: Optional[Dict[str, Any]] = None):
        """
        Initialize rate limit evaluator.
        
        Config format:
        {
            "limits": [
                {
                    "category": "high_value_transaction",
                    "max_count": 3,
                    "window_hours": 24,
                    "reason": "Daily transaction limit reached"
                }
            ]
        }
        """
        super().__init__(name, enabled, config)
        self.limits = self.config.get("limits", [])
    
    async def evaluate(
        self,
        user_id: str,
        requested_action: str,
        requested_category: ActionCategory,
        action_history: UserActionHistory,
        request_details: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        """Evaluate based on rate limits."""
        if not self.enabled:
            return EvaluationResult(allowed=True)
        
        # Check each limit
        for limit in self.limits:
            limit_cat_str = limit.get("category")
            limit_category = ActionCategory(limit_cat_str)
            
            if requested_category != limit_category:
                continue
            
            max_count = limit.get("max_count", 5)
            window_hours = limit.get("window_hours", 24)
            reason_template = limit.get("reason", "Rate limit exceeded")
            
            # Count recent actions in this category
            count = action_history.count_actions(
                user_id=user_id,
                action_category=limit_category,
                since_hours=window_hours
            )
            
            if count >= max_count:
                reason = (
                    f"{reason_template}. "
                    f"You have performed {count} {limit_category.value} action(s) "
                    f"in the last {window_hours} hours. Maximum allowed: {max_count}."
                )
                
                # Calculate when limit resets
                oldest_action = action_history.get_user_actions(
                    user_id=user_id,
                    categories=[limit_category],
                    since_hours=window_hours,
                    limit=max_count
                )[-1]
                
                blocked_until = oldest_action.timestamp + timedelta(hours=window_hours)
                
                return EvaluationResult(
                    allowed=False,
                    reason=reason,
                    evaluator_name=self.name,
                    blocked_until=blocked_until,
                    metadata={
                        "current_count": count,
                        "max_count": max_count,
                        "window_hours": window_hours
                    }
                )
        
        # No limits exceeded
        return EvaluationResult(allowed=True)


class ThresholdEvaluator(ActionEvaluator):
    """
    Evaluator that checks value thresholds.
    
    Example: Transactions over $10,000 require additional verification.
    """
    
    def __init__(self, name: str, enabled: bool = True, config: Optional[Dict[str, Any]] = None):
        """
        Initialize threshold evaluator.
        
        Config format:
        {
            "thresholds": [
                {
                    "category": "high_value_transaction",
                    "field": "amount",
                    "max_value": 10000,
                    "reason": "Transaction amount exceeds allowed limit"
                }
            ]
        }
        """
        super().__init__(name, enabled, config)
        self.thresholds = self.config.get("thresholds", [])
    
    async def evaluate(
        self,
        user_id: str,
        requested_action: str,
        requested_category: ActionCategory,
        action_history: UserActionHistory,
        request_details: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        """Evaluate based on value thresholds."""
        if not self.enabled:
            return EvaluationResult(allowed=True)
        
        # Check each threshold
        for threshold in self.thresholds:
            threshold_cat_str = threshold.get("category")
            threshold_category = ActionCategory(threshold_cat_str)
            
            if requested_category != threshold_category:
                continue
            
            field = threshold.get("field", "amount")
            max_value = threshold.get("max_value")
            reason_template = threshold.get("reason", "Value exceeds threshold")
            
            # Extract value from request details
            value = self._extract_value(request_details, field)
            
            if value is not None and max_value is not None and value > max_value:
                reason = (
                    f"{reason_template}. "
                    f"Provided {field}: {value}, Maximum allowed: {max_value}."
                )
                
                return EvaluationResult(
                    allowed=False,
                    reason=reason,
                    evaluator_name=self.name,
                    metadata={
                        "field": field,
                        "value": value,
                        "max_value": max_value
                    }
                )
        
        # No thresholds exceeded
        return EvaluationResult(allowed=True)


# Global action history instance
_global_action_history: Optional[UserActionHistory] = None


def get_action_history() -> UserActionHistory:
    """Get or create global action history instance."""
    global _global_action_history
    if _global_action_history is None:
        _global_action_history = UserActionHistory()
    return _global_action_history
