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
        Simplified hybrid reasoning: AI-first with step-by-step thinking.
        Rules serve as validation or quick-path for very specific queries.

        Args:
            input_data: Input data
            available_agents: Available agents

        Returns:
            ReasoningResult or None
        """
        logger.debug("Using AI-first hybrid reasoning with step-by-step planning")

        # Step 1: Use AI as primary reasoner with step-by-step thinking
        logger.info("AI reasoner analyzing query with step-by-step approach")
        ai_plan = await self.ai_reasoner.reason(input_data, available_agents)

        # Step 2: Check if rules match for validation
        rule_matches = self.rule_engine.evaluate(input_data)
        
        if rule_matches:
            best_match = rule_matches[0]
            logger.info(
                f"Rule matched: '{best_match.rule_name}' (confidence={best_match.confidence:.2f})"
            )
            
            # If AI agrees with rules or rules have very high confidence, prefer rule result
            if ai_plan and best_match.confidence >= 0.95:
                if set(ai_plan.agents) == set(best_match.target_agents):
                    logger.info("AI agrees with high-confidence rule")
                    return ReasoningResult(
                        agents=best_match.target_agents,
                        confidence=best_match.confidence,
                        method="rule_validated",
                        reasoning=f"Rule '{best_match.rule_name}' validated by AI: {ai_plan.reasoning}",
                        parallel=False,
                        parameters=ai_plan.parameters if ai_plan else {},
                        rule_matches=rule_matches,
                        ai_plan=ai_plan,
                    )

        # Step 3: Return AI reasoning result (primary decision maker)
        if ai_plan:
            # Validate AI plan
            is_valid = await self.ai_reasoner.validate_plan(ai_plan, available_agents)
            
            if is_valid:
                logger.info(
                    f"AI reasoning complete: {ai_plan.agents} (confidence={ai_plan.confidence:.2f})"
                )
                return ReasoningResult(
                    agents=ai_plan.agents,
                    confidence=ai_plan.confidence,
                    method="ai",
                    reasoning=ai_plan.reasoning,
                    parallel=ai_plan.parallel,
                    parameters=ai_plan.parameters,
                    rule_matches=rule_matches,
                    ai_plan=ai_plan,
                )
            else:
                logger.warning("AI plan validation failed")
        
        # Step 4: Fallback to rules if AI failed
        if rule_matches:
            best_match = rule_matches[0]
            logger.info("Falling back to rule match")
            return ReasoningResult(
                agents=best_match.target_agents,
                confidence=best_match.confidence * 0.8,
                method="rule_fallback",
                reasoning=f"Rule '{best_match.rule_name}' (AI fallback)",
                parallel=False,
                rule_matches=rule_matches,
            )
        
        # No valid reasoning found
        logger.warning("No valid agents found for query")
        return None

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
