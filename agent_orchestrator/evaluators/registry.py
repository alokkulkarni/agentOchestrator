"""
Evaluator registry for managing and executing action evaluators.

This module provides:
- Loading evaluators from YAML configuration
- Registry to manage multiple evaluators
- Batch evaluation of all configured evaluators
- Integration with orchestrator
"""

import logging
from typing import Any, Dict, List, Optional

from . import (
    ActionCategory,
    ActionEvaluator,
    EvaluationResult,
    RateLimitEvaluator,
    ThresholdEvaluator,
    TimedRestrictionEvaluator,
    UserActionHistory,
)

logger = logging.getLogger(__name__)


class EvaluatorRegistry:
    """
    Registry for managing action evaluators.
    
    Features:
    - Load evaluators from configuration
    - Execute all evaluators in sequence
    - Aggregate results
    - Extensible with custom evaluators
    """
    
    # Built-in evaluator types
    EVALUATOR_TYPES = {
        "timed_restriction": TimedRestrictionEvaluator,
        "rate_limit": RateLimitEvaluator,
        "threshold": ThresholdEvaluator,
    }
    
    def __init__(self, action_history: UserActionHistory):
        """
        Initialize evaluator registry.
        
        Args:
            action_history: User action history tracker
        """
        self.action_history = action_history
        self.evaluators: List[ActionEvaluator] = []
        
    def register_evaluator(self, evaluator: ActionEvaluator):
        """Register a new evaluator."""
        self.evaluators.append(evaluator)
        logger.info(f"Registered evaluator: {evaluator.name} (enabled: {evaluator.enabled})")
    
    def load_from_config(self, config: Dict[str, Any]):
        """
        Load evaluators from configuration.
        
        Config format:
        {
            "evaluators": [
                {
                    "name": "address_change_restriction",
                    "type": "timed_restriction",
                    "enabled": true,
                    "config": {...}
                }
            ]
        }
        
        Args:
            config: Configuration dictionary
        """
        evaluator_configs = config.get("evaluators", [])
        
        for eval_config in evaluator_configs:
            name = eval_config.get("name", "unnamed")
            evaluator_type = eval_config.get("type")
            enabled = eval_config.get("enabled", True)
            eval_specific_config = eval_config.get("config", {})
            
            # Get evaluator class
            evaluator_class = self.EVALUATOR_TYPES.get(evaluator_type)
            
            if not evaluator_class:
                logger.warning(
                    f"Unknown evaluator type: {evaluator_type} for evaluator {name}"
                )
                continue
            
            # Create evaluator instance
            try:
                evaluator = evaluator_class(
                    name=name,
                    enabled=enabled,
                    config=eval_specific_config
                )
                self.register_evaluator(evaluator)
                logger.info(f"Loaded evaluator: {name} (type: {evaluator_type})")
            except Exception as e:
                logger.error(
                    f"Failed to create evaluator {name} of type {evaluator_type}: {e}"
                )
    
    async def evaluate_action(
        self,
        user_id: str,
        requested_action: str,
        requested_category: ActionCategory,
        request_details: Optional[Dict[str, Any]] = None,
        stop_on_first_denial: bool = True
    ) -> EvaluationResult:
        """
        Evaluate if an action is allowed by running all evaluators.
        
        Args:
            user_id: User requesting the action
            requested_action: Action type being requested
            requested_category: Category of requested action
            request_details: Additional request details
            stop_on_first_denial: Stop evaluating after first denial
            
        Returns:
            EvaluationResult - allowed if all evaluators pass, denied otherwise
        """
        if not self.evaluators:
            # No evaluators configured - allow by default
            return EvaluationResult(allowed=True)
        
        # Run each evaluator
        for evaluator in self.evaluators:
            if not evaluator.enabled:
                continue
            
            try:
                result = await evaluator.evaluate(
                    user_id=user_id,
                    requested_action=requested_action,
                    requested_category=requested_category,
                    action_history=self.action_history,
                    request_details=request_details
                )
                
                # If denied and stop_on_first_denial, return immediately
                if not result.allowed:
                    logger.warning(
                        f"Action denied by evaluator '{evaluator.name}': "
                        f"{result.reason}"
                    )
                    if stop_on_first_denial:
                        return result
                
            except Exception as e:
                logger.error(
                    f"Error evaluating action with {evaluator.name}: {e}",
                    exc_info=True
                )
                # Continue with other evaluators on error
        
        # All evaluators passed
        return EvaluationResult(allowed=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about registered evaluators."""
        return {
            "total_evaluators": len(self.evaluators),
            "enabled_evaluators": sum(1 for e in self.evaluators if e.enabled),
            "evaluator_names": [e.name for e in self.evaluators],
        }
    
    @classmethod
    def register_custom_evaluator_type(cls, type_name: str, evaluator_class):
        """
        Register a custom evaluator type.
        
        Args:
            type_name: Name to use in configuration
            evaluator_class: Evaluator class (must inherit from ActionEvaluator)
        """
        cls.EVALUATOR_TYPES[type_name] = evaluator_class
        logger.info(f"Registered custom evaluator type: {type_name}")


def map_query_to_action_category(query: str, agent_name: Optional[str] = None) -> ActionCategory:
    """
    Map user query and agent name to an action category.
    
    This function uses heuristics to determine what category of action
    the user is attempting.
    
    Args:
        query: User's query text
        agent_name: Name of agent being called (if known)
        
    Returns:
        ActionCategory enum value
    """
    query_lower = query.lower()
    
    # Profile/account changes
    if any(word in query_lower for word in ["change address", "update address", "move", "relocate"]):
        return ActionCategory.ADDRESS_CHANGE
    
    if any(word in query_lower for word in ["change password", "update password", "reset password"]):
        return ActionCategory.PASSWORD_CHANGE
    
    if any(word in query_lower for word in ["change payment", "update payment", "add card", "remove card"]):
        return ActionCategory.PAYMENT_METHOD_CHANGE
    
    # Transactions
    if any(word in query_lower for word in ["order card", "request card", "new card"]):
        return ActionCategory.CARD_ORDER
    
    if any(word in query_lower for word in ["transfer", "send money", "pay", "payment"]):
        # Check for high value indicators
        if any(word in query_lower for word in ["$10000", "$5000", "10000", "5000", "large"]):
            return ActionCategory.HIGH_VALUE_TRANSACTION
        return ActionCategory.TRANSFER
    
    if any(word in query_lower for word in ["buy", "purchase", "order"]):
        return ActionCategory.PURCHASE
    
    if any(word in query_lower for word in ["close account", "delete account", "cancel account"]):
        return ActionCategory.ACCOUNT_CLOSURE
    
    # Check agent name for clues
    if agent_name:
        agent_lower = agent_name.lower()
        if "transaction" in agent_lower:
            return ActionCategory.HIGH_VALUE_TRANSACTION
        if "payment" in agent_lower or "card" in agent_lower:
            return ActionCategory.CARD_ORDER
    
    # Default to query for information-only requests
    if any(word in query_lower for word in ["what", "how", "when", "where", "search", "find", "tell"]):
        return ActionCategory.QUERY
    
    return ActionCategory.OTHER
