"""Tests for reasoning engines."""

import pytest

from agent_orchestrator.agents import DirectAgent
from agent_orchestrator.config import DirectToolConfig
from agent_orchestrator.reasoning import RuleEngine


class TestRuleEngine:
    """Test rule-based reasoning engine."""

    def test_rule_evaluation_match(self, rule_engine, mock_input_data):
        """Test rule evaluation with matching input."""
        matches = rule_engine.evaluate(mock_input_data)

        assert len(matches) > 0
        assert matches[0].matched is True
        assert "calculator" in matches[0].target_agents

    def test_rule_evaluation_no_match(self, rule_engine):
        """Test rule evaluation with non-matching input."""
        input_data = {
            "query": "something unrelated",
        }

        matches = rule_engine.evaluate(input_data)

        # May have no matches or low-priority matches
        if matches:
            # If there are matches, they should have lower confidence
            assert all(m.confidence < 0.9 for m in matches)

    def test_get_best_match(self, rule_engine, mock_input_data):
        """Test getting best matching rule."""
        best_match = rule_engine.get_best_match(mock_input_data)

        assert best_match is not None
        assert best_match.matched is True
        assert len(best_match.target_agents) > 0

    def test_high_confidence_matches(self, rule_engine, mock_input_data):
        """Test filtering high-confidence matches."""
        high_conf_matches = rule_engine.get_high_confidence_matches(
            mock_input_data,
            min_confidence=0.8
        )

        assert len(high_conf_matches) > 0
        assert all(m.confidence >= 0.8 for m in high_conf_matches)


class TestRuleConditions:
    """Test rule condition evaluation."""

    def test_contains_operator(self, rule_engine):
        """Test contains operator."""
        input_data = {"query": "calculate the sum"}
        matches = rule_engine.evaluate(input_data)

        assert len(matches) > 0

    def test_case_insensitive_matching(self, rule_engine):
        """Test case-insensitive matching."""
        input_data1 = {"query": "CALCULATE"}
        input_data2 = {"query": "calculate"}

        matches1 = rule_engine.evaluate(input_data1)
        matches2 = rule_engine.evaluate(input_data2)

        # Both should match since case_sensitive=False
        assert len(matches1) > 0
        assert len(matches2) > 0

    def test_exists_operator(self, sample_rules_config):
        """Test exists operator."""
        from agent_orchestrator.config import RuleCondition, RuleConfig

        # Add a rule with exists operator
        sample_rules_config.rules.append(
            RuleConfig(
                name="has_data",
                priority=50,
                conditions=[
                    RuleCondition(
                        field="data",
                        operator="exists",
                        value=None,
                    )
                ],
                logic="and",
                target_agents=["processor"],
                confidence=0.7,
                enabled=True,
            )
        )

        engine = RuleEngine(sample_rules_config)

        # Should match when field exists
        matches = engine.evaluate({"data": {"some": "value"}})
        assert any(m.rule_name == "has_data" for m in matches)

        # Should not match when field doesn't exist
        matches = engine.evaluate({"other": "value"})
        assert not any(m.rule_name == "has_data" for m in matches)
