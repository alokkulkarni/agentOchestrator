"""
Rule-based reasoning engine for agent routing.

This module implements pattern-based routing using configurable rules.
Rules are evaluated against input data to determine which agents should be called.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from ..config.models import RuleCondition, RuleConfig, RuleOperator, RulesFileConfig

logger = logging.getLogger(__name__)


class RuleMatchResult:
    """Result of rule evaluation."""

    def __init__(
        self,
        matched: bool,
        rule_name: str,
        target_agents: List[str],
        confidence: float,
        matched_conditions: List[str],
    ):
        """
        Initialize rule match result.

        Args:
            matched: Whether the rule matched
            rule_name: Name of the rule
            target_agents: Agents to route to if matched
            confidence: Confidence score for this match
            matched_conditions: List of conditions that matched
        """
        self.matched = matched
        self.rule_name = rule_name
        self.target_agents = target_agents
        self.confidence = confidence
        self.matched_conditions = matched_conditions

    def __repr__(self) -> str:
        return (
            f"RuleMatchResult(rule={self.rule_name}, matched={self.matched}, "
            f"confidence={self.confidence:.2f}, agents={self.target_agents})"
        )


class RuleEngine:
    """
    Rule-based routing engine.

    Evaluates rules against input data using pattern matching, keyword detection,
    and regex patterns. Supports AND/OR/NOT logic for combining conditions.
    """

    def __init__(self, rules_config: RulesFileConfig):
        """
        Initialize rule engine with rules configuration.

        Args:
            rules_config: Rules configuration loaded from YAML
        """
        self.rules_config = rules_config
        self.rules = rules_config.get_sorted_rules()  # Sorted by priority
        self._compiled_patterns: Dict[str, re.Pattern] = {}

        # Pre-compile regex patterns for performance
        self._compile_patterns()

        logger.info(f"Rule engine initialized with {len(self.rules)} rules")

    def _compile_patterns(self) -> None:
        """Pre-compile all regex patterns in rules for performance."""
        for rule in self.rules:
            for condition in rule.conditions:
                if condition.operator == "regex" and condition.value:
                    pattern_key = f"{rule.name}_{condition.field}_{condition.value}"
                    try:
                        flags = 0 if condition.case_sensitive else re.IGNORECASE
                        self._compiled_patterns[pattern_key] = re.compile(
                            condition.value, flags
                        )
                    except re.error as e:
                        logger.error(
                            f"Invalid regex pattern in rule '{rule.name}', "
                            f"condition '{condition.field}': {e}"
                        )

    def _get_field_value(self, input_data: Dict[str, Any], field: str) -> Optional[Any]:
        """
        Get field value from input data, supporting nested keys.

        Args:
            input_data: Input data dictionary
            field: Field name (supports dot notation, e.g., "user.name")

        Returns:
            Field value or None if not found
        """
        keys = field.split(".")
        value = input_data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value

    def _evaluate_condition(
        self,
        condition: RuleCondition,
        input_data: Dict[str, Any],
        rule_name: str,
    ) -> bool:
        """
        Evaluate a single condition against input data.

        Args:
            condition: Rule condition to evaluate
            input_data: Input data to check
            rule_name: Name of the rule (for logging/caching)

        Returns:
            True if condition matches
        """
        field_value = self._get_field_value(input_data, condition.field)

        # Handle "exists" operator
        if condition.operator == "exists":
            return field_value is not None

        # For other operators, field must exist and be a string
        if field_value is None:
            return False

        # Convert to string for comparison
        field_str = str(field_value)
        condition_value = condition.value or ""

        # Apply case sensitivity
        if not condition.case_sensitive:
            field_str = field_str.lower()
            condition_value = condition_value.lower()

        # Evaluate based on operator
        if condition.operator == "equals":
            return field_str == condition_value

        elif condition.operator == "contains":
            return condition_value in field_str

        elif condition.operator == "regex":
            pattern_key = f"{rule_name}_{condition.field}_{condition.value}"
            pattern = self._compiled_patterns.get(pattern_key)
            if pattern:
                return bool(pattern.search(field_str))
            else:
                logger.warning(f"No compiled pattern found for {pattern_key}")
                return False

        else:
            logger.warning(f"Unknown operator: {condition.operator}")
            return False

    def _evaluate_rule(
        self,
        rule: RuleConfig,
        input_data: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        Evaluate all conditions in a rule.

        Args:
            rule: Rule to evaluate
            input_data: Input data to check

        Returns:
            Tuple of (matched, list of matched condition descriptions)
        """
        condition_results = []
        matched_conditions = []

        for condition in rule.conditions:
            result = self._evaluate_condition(condition, input_data, rule.name)
            condition_results.append(result)
            if result:
                matched_conditions.append(
                    f"{condition.field} {condition.operator} '{condition.value}'"
                )

        # Apply logic operator
        if rule.logic == RuleOperator.AND:
            matched = all(condition_results)
        elif rule.logic == RuleOperator.OR:
            matched = any(condition_results)
        elif rule.logic == RuleOperator.NOT:
            matched = not all(condition_results)
        else:
            logger.warning(f"Unknown logic operator: {rule.logic}")
            matched = False

        return matched, matched_conditions

    def evaluate(self, input_data: Dict[str, Any]) -> List[RuleMatchResult]:
        """
        Evaluate all rules against input data.

        Rules are evaluated in priority order (highest first).
        Returns all matching rules.

        Args:
            input_data: Input data to route

        Returns:
            List of rule match results (all matches, ordered by priority)
        """
        matches = []

        logger.debug(f"Evaluating {len(self.rules)} rules against input")

        for rule in self.rules:
            if not rule.enabled:
                continue

            matched, matched_conditions = self._evaluate_rule(rule, input_data)

            if matched:
                logger.info(
                    f"Rule '{rule.name}' matched (priority={rule.priority}, "
                    f"confidence={rule.confidence})"
                )
                matches.append(
                    RuleMatchResult(
                        matched=True,
                        rule_name=rule.name,
                        target_agents=rule.target_agents,
                        confidence=rule.confidence,
                        matched_conditions=matched_conditions,
                    )
                )
            else:
                logger.debug(f"Rule '{rule.name}' did not match")

        if not matches:
            logger.info("No rules matched the input")

        return matches

    def get_best_match(self, input_data: Dict[str, Any]) -> Optional[RuleMatchResult]:
        """
        Get the best matching rule (highest priority).

        Args:
            input_data: Input data to route

        Returns:
            Best rule match or None if no matches
        """
        matches = self.evaluate(input_data)
        return matches[0] if matches else None

    def get_high_confidence_matches(
        self,
        input_data: Dict[str, Any],
        min_confidence: float = 0.8,
    ) -> List[RuleMatchResult]:
        """
        Get all matches with confidence above threshold.

        Args:
            input_data: Input data to route
            min_confidence: Minimum confidence threshold (0.0 to 1.0)

        Returns:
            List of high-confidence matches
        """
        all_matches = self.evaluate(input_data)
        return [m for m in all_matches if m.confidence >= min_confidence]

    def reload_rules(self, rules_config: RulesFileConfig) -> None:
        """
        Reload rules from new configuration.

        Args:
            rules_config: New rules configuration
        """
        logger.info("Reloading rules")
        self.rules_config = rules_config
        self.rules = rules_config.get_sorted_rules()
        self._compiled_patterns.clear()
        self._compile_patterns()
        logger.info(f"Rules reloaded: {len(self.rules)} active rules")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get rule engine statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "total_rules": len(self.rules_config.rules),
            "enabled_rules": len(self.rules),
            "rule_names": [r.name for r in self.rules],
            "priorities": [r.priority for r in self.rules],
            "avg_confidence": sum(r.confidence for r in self.rules) / len(self.rules)
            if self.rules
            else 0.0,
        }
