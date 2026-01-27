"""
Hybrid reasoning engine combining rule-based and AI-based approaches.

This module provides a reasoning engine that tries rule-based routing first
(fast, deterministic) and falls back to AI reasoning when rules don't match
or have low confidence.
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from ..agents.base_agent import BaseAgent
from ..config.models import ReasoningMode
from .ai_reasoner import AIReasoner, AgentPlan
from .rule_engine import RuleEngine, RuleMatchResult

logger = logging.getLogger(__name__)


class ReasoningResult:
    """Result from hybrid reasoner."""

    def __init__(
        self,
        agents: List[str],
        confidence: float,
        method: str,  # "rule", "ai", or "hybrid"
        reasoning: str,
        parallel: bool = False,
        parameters: Optional[Dict[str, Dict[str, Any]]] = None,
        rule_matches: Optional[List[RuleMatchResult]] = None,
        ai_plan: Optional[AgentPlan] = None,
    ):
        """
        Initialize reasoning result.

        Args:
            agents: List of agent names to call
            confidence: Overall confidence score (0.0 to 1.0)
            method: Reasoning method used ("rule", "ai", or "hybrid")
            reasoning: Explanation of the decision
            parallel: Whether agents can be called in parallel
            parameters: Agent-specific parameters
            rule_matches: Rule matches (if rules were used)
            ai_plan: AI plan (if AI was used)
        """
        self.agents = agents
        self.confidence = confidence
        self.method = method
        self.reasoning = reasoning
        self.parallel = parallel
        self.parameters = parameters or {}
        self.rule_matches = rule_matches or []
        self.ai_plan = ai_plan

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "agents": self.agents,
            "confidence": self.confidence,
            "method": self.method,
            "reasoning": self.reasoning,
            "parallel": self.parallel,
            "parameters": self.parameters,
            "rule_matches": [
                {
                    "rule_name": m.rule_name,
                    "confidence": m.confidence,
                    "matched_conditions": m.matched_conditions,
                }
                for m in self.rule_matches
            ],
            "ai_plan": self.ai_plan.to_dict() if self.ai_plan else None,
        }

    def __repr__(self) -> str:
        return (
            f"ReasoningResult(method={self.method}, agents={self.agents}, "
            f"confidence={self.confidence:.2f})"
        )


class HybridReasoner:
    """
    Hybrid reasoning engine combining rule-based and AI approaches.

    Strategy:
    1. Rule-first: Try rule engine first, use AI if no matches or low confidence
    2. AI-first: Try AI first, validate with rules
    3. Parallel: Run both and combine results
    """

    def __init__(
        self,
        rule_engine: RuleEngine,
        ai_reasoner: AIReasoner,
        mode: ReasoningMode = ReasoningMode.HYBRID,
        rule_confidence_threshold: float = 0.7,
    ):
        """
        Initialize hybrid reasoner.

        Args:
            rule_engine: Rule-based reasoning engine
            ai_reasoner: AI-based reasoning engine
            mode: Reasoning mode (rule, ai, or hybrid)
            rule_confidence_threshold: Minimum confidence for rule-only routing
        """
        self.rule_engine = rule_engine
        self.ai_reasoner = ai_reasoner
        self.mode = mode
        self.rule_confidence_threshold = rule_confidence_threshold

        logger.info(
            f"Hybrid reasoner initialized: mode={mode}, "
            f"threshold={rule_confidence_threshold}"
        )

    async def reason(
        self,
        input_data: Dict[str, Any],
        available_agents: List[BaseAgent],
    ) -> Optional[ReasoningResult]:
        """
        Determine which agents to call using hybrid approach.

        Args:
            input_data: Input data to analyze
            available_agents: List of available agents

        Returns:
            ReasoningResult with execution plan, or None if reasoning fails
        """
        if not available_agents:
            logger.warning("No available agents for reasoning")
            return None

        logger.info(f"Hybrid reasoner analyzing input (mode={self.mode})")

        # Route based on mode
        if self.mode == ReasoningMode.RULE:
            return self._rule_only(input_data, available_agents)
        elif self.mode == ReasoningMode.AI:
            return await self._ai_only(input_data, available_agents)
        else:  # HYBRID
            return await self._hybrid_reasoning(input_data, available_agents)

    def _rule_only(
        self,
        input_data: Dict[str, Any],
        available_agents: List[BaseAgent],
    ) -> Optional[ReasoningResult]:
        """
        Use only rule-based reasoning.

        Args:
            input_data: Input data
            available_agents: Available agents

        Returns:
            ReasoningResult or None
        """
        logger.debug("Using rule-only reasoning")
        rule_matches = self.rule_engine.evaluate(input_data)

        if not rule_matches:
            logger.warning("No rule matches found")
            return None

        # Use best match
        best_match = rule_matches[0]

        return ReasoningResult(
            agents=best_match.target_agents,
            confidence=best_match.confidence,
            method="rule",
            reasoning=f"Rule '{best_match.rule_name}' matched: {', '.join(best_match.matched_conditions)}",
            parallel=False,  # Rules don't specify parallelism
            rule_matches=rule_matches,
        )

    async def _ai_only(
        self,
        input_data: Dict[str, Any],
        available_agents: List[BaseAgent],
    ) -> Optional[ReasoningResult]:
        """
        Use only AI-based reasoning.

        Args:
            input_data: Input data
            available_agents: Available agents

        Returns:
            ReasoningResult or None
        """
        logger.debug("Using AI-only reasoning")
        ai_plan = await self.ai_reasoner.reason(input_data, available_agents)

        if not ai_plan:
            logger.warning("AI reasoning failed")
            return None

        # Validate plan
        is_valid = await self.ai_reasoner.validate_plan(ai_plan, available_agents)
        if not is_valid:
            logger.warning("AI plan validation failed")
            return None

        return ReasoningResult(
            agents=ai_plan.agents,
            confidence=ai_plan.confidence,
            method="ai",
            reasoning=ai_plan.reasoning,
            parallel=ai_plan.parallel,
            parameters=ai_plan.parameters,
            ai_plan=ai_plan,
        )

    async def _hybrid_reasoning(
        self,
        input_data: Dict[str, Any],
        available_agents: List[BaseAgent],
    ) -> Optional[ReasoningResult]:
        """
        Use hybrid reasoning: rules first, AI fallback.

        Args:
            input_data: Input data
            available_agents: Available agents

        Returns:
            ReasoningResult or None
        """
        logger.debug("Using hybrid reasoning")

        # Step 1: Try rule engine
        rule_matches = self.rule_engine.evaluate(input_data)

        if rule_matches:
            # Get all high-confidence matches
            high_confidence_matches = [
                m for m in rule_matches
                if m.confidence >= self.rule_confidence_threshold
            ]

            if high_confidence_matches:
                # Check if multiple high-confidence rules matched (multi-intent query)
                if len(high_confidence_matches) > 1:
                    # Combine agents from all high-confidence matches
                    all_agents = []
                    seen_agents = set()
                    rule_names = []

                    for match in high_confidence_matches:
                        rule_names.append(match.rule_name)
                        for agent in match.target_agents:
                            if agent not in seen_agents:
                                all_agents.append(agent)
                                seen_agents.add(agent)

                    avg_confidence = sum(m.confidence for m in high_confidence_matches) / len(high_confidence_matches)

                    logger.info(
                        f"Multiple rules matched with high confidence (avg={avg_confidence:.2f}), "
                        f"validating with AI: {rule_names}"
                    )

                    # Validate multi-agent selection with AI
                    validation = await self.ai_reasoner.validate_rule_selection(
                        input_data=input_data,
                        rule_selected_agents=all_agents,
                        available_agents=available_agents,
                        rule_name=f"multiple: {', '.join(rule_names)}",
                    )

                    if validation["is_valid"]:
                        # AI validated the multi-agent selection
                        logger.info(
                            f"AI validated multi-agent selection (confidence={validation['confidence']:.2f})"
                        )
                        return ReasoningResult(
                            agents=all_agents,
                            confidence=avg_confidence,
                            method="rule_multi_validated",
                            reasoning=f"Multiple rules validated by AI: {', '.join(rule_names)}. {validation['reasoning']}",
                            parallel=True,  # Multiple intents can be processed in parallel
                            parameters=validation.get("parameters", {}),
                            rule_matches=rule_matches,
                        )
                    else:
                        # AI rejected multi-agent selection
                        logger.warning(
                            f"AI rejected multi-agent selection: {validation['reasoning']}"
                        )

                        suggested_agents = validation.get("suggested_agents", [])
                        ai_confidence = validation.get("confidence", 0)
                        
                        # Only use AI override if confidence is reasonable (>= 0.5)
                        if ai_confidence < 0.5:
                            logger.info(
                                f"AI override confidence too low ({ai_confidence:.2f}), "
                                f"returning no match instead of incorrect suggestion"
                            )
                            return None
                        
                        if suggested_agents:
                            # Filter to only include available agents
                            available_names = {agent.name for agent in available_agents}
                            valid_suggested = [a for a in suggested_agents if a in available_names]

                            if valid_suggested:
                                logger.info(
                                    f"Using AI-suggested agents (confidence: {ai_confidence:.2f}): {valid_suggested}"
                                )
                                return ReasoningResult(
                                    agents=valid_suggested,
                                    confidence=ai_confidence,
                                    method="ai_override",
                                    reasoning=f"AI override of multi-rule: {validation['reasoning']}",
                                    parameters=validation.get("parameters", {}),
                                    parallel=False,
                                    rule_matches=rule_matches,
                                )

                        # No valid suggestions, fall back to full AI reasoning
                        logger.info("No valid AI suggestions for multi-agent, falling back to full AI reasoning")
                        # Continue to Step 2 below
                else:
                    # Single high-confidence match - validate with AI before using
                    best_match = high_confidence_matches[0]
                    logger.info(
                        f"Rule engine matched with high confidence ({best_match.confidence:.2f}), "
                        f"validating with AI"
                    )

                    # Validate rule selection with AI
                    validation = await self.ai_reasoner.validate_rule_selection(
                        input_data=input_data,
                        rule_selected_agents=best_match.target_agents,
                        available_agents=available_agents,
                        rule_name=best_match.rule_name,
                    )

                    if validation["is_valid"]:
                        # AI validated the rule selection
                        logger.info(
                            f"AI validated rule selection (confidence={validation['confidence']:.2f}): "
                            f"{validation['reasoning']}"
                        )
                        return ReasoningResult(
                            agents=best_match.target_agents,
                            confidence=best_match.confidence,
                            method="rule_validated",
                            reasoning=f"Rule '{best_match.rule_name}' validated by AI: {validation['reasoning']}",
                            parallel=False,
                            parameters=validation.get("parameters", {}),
                            rule_matches=rule_matches,
                        )
                    else:
                        # AI rejected rule selection, use AI's suggested agents
                        ai_confidence = validation.get("confidence", 0)
                        logger.warning(
                            f"AI rejected rule selection (confidence={ai_confidence:.2f}): "
                            f"{validation['reasoning']}"
                        )

                        # Only use AI override if confidence is reasonable (>= 0.5)
                        if ai_confidence < 0.5:
                            logger.info(
                                f"AI override confidence too low ({ai_confidence:.2f}), "
                                f"returning no match instead of incorrect suggestion"
                            )
                            return None

                        suggested_agents = validation.get("suggested_agents", [])
                        if suggested_agents:
                            # Filter to only include available agents
                            available_names = {agent.name for agent in available_agents}
                            valid_suggested = [a for a in suggested_agents if a in available_names]

                            if valid_suggested:
                                logger.info(
                                    f"Using AI-suggested agents (confidence: {ai_confidence:.2f}): {valid_suggested}"
                                )
                                return ReasoningResult(
                                    agents=valid_suggested,
                                    confidence=ai_confidence,
                                    method="ai_override",
                                    reasoning=f"AI override: {validation['reasoning']}",
                                    parallel=False,
                                    parameters=validation.get("parameters", {}),
                                    rule_matches=rule_matches,
                                )

                        # No valid suggested agents, fall back to full AI reasoning
                        logger.info("No valid AI suggestions, falling back to full AI reasoning")
                        # Continue to Step 2 below
            else:
                # No high-confidence matches
                best_match = rule_matches[0]
                logger.info(
                    f"Rule matched but confidence low ({best_match.confidence:.2f}), "
                    f"consulting AI"
                )

        # Step 2: No matches or low confidence, use AI
        logger.info("Using AI reasoner for final decision")
        ai_plan = await self.ai_reasoner.reason(input_data, available_agents)

        if not ai_plan:
            # AI failed, fall back to best rule match if available
            if rule_matches:
                logger.warning("AI reasoning failed, falling back to rule match")
                best_match = rule_matches[0]
                return ReasoningResult(
                    agents=best_match.target_agents,
                    confidence=best_match.confidence * 0.8,  # Reduce confidence
                    method="rule_fallback",
                    reasoning=f"AI failed, using rule '{best_match.rule_name}': {', '.join(best_match.matched_conditions)}",
                    parallel=False,
                    rule_matches=rule_matches,
                )
            else:
                logger.error("Both rule and AI reasoning failed")
                return None

        # Validate AI plan
        is_valid = await self.ai_reasoner.validate_plan(ai_plan, available_agents)

        if not is_valid:
            logger.warning("AI plan invalid, falling back to rules")
            if rule_matches:
                best_match = rule_matches[0]
                return ReasoningResult(
                    agents=best_match.target_agents,
                    confidence=best_match.confidence,
                    method="rule_fallback",
                    reasoning=f"AI plan invalid, using rule '{best_match.rule_name}'",
                    parallel=False,
                    rule_matches=rule_matches,
                )
            return None

        # Return AI result with rule context
        return ReasoningResult(
            agents=ai_plan.agents,
            confidence=ai_plan.confidence,
            method="hybrid",
            reasoning=f"AI reasoning: {ai_plan.reasoning}",
            parallel=ai_plan.parallel,
            parameters=ai_plan.parameters,
            rule_matches=rule_matches,
            ai_plan=ai_plan,
        )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get hybrid reasoner statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "mode": self.mode.value,
            "rule_confidence_threshold": self.rule_confidence_threshold,
            "rule_engine_stats": self.rule_engine.get_stats(),
            "ai_reasoner_stats": self.ai_reasoner.get_stats(),
        }
