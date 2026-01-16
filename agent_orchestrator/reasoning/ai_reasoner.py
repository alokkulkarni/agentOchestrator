"""
AI-based reasoning engine using Claude for intelligent agent routing.

This module uses Claude (via Anthropic SDK) to analyze input and determine
which agents should be called, in what order, and with what parameters.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from anthropic import Anthropic, AsyncAnthropic
from anthropic.types import Message

from ..agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class AgentPlan:
    """Execution plan from AI reasoner."""

    def __init__(
        self,
        agents: List[str],
        reasoning: str,
        confidence: float,
        parallel: bool = False,
        parameters: Optional[Dict[str, Dict[str, Any]]] = None,
    ):
        """
        Initialize agent plan.

        Args:
            agents: List of agent names to call
            reasoning: Explanation of why these agents were selected
            confidence: Confidence score (0.0 to 1.0)
            parallel: Whether agents can be called in parallel
            parameters: Optional parameters for each agent {agent_name: params}
        """
        self.agents = agents
        self.reasoning = reasoning
        self.confidence = confidence
        self.parallel = parallel
        self.parameters = parameters or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary."""
        return {
            "agents": self.agents,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "parallel": self.parallel,
            "parameters": self.parameters,
        }

    def __repr__(self) -> str:
        mode = "parallel" if self.parallel else "sequential"
        return (
            f"AgentPlan(agents={self.agents}, confidence={self.confidence:.2f}, "
            f"mode={mode})"
        )


class AIReasoner:
    """
    AI-based reasoning engine using Claude.

    Uses Claude to analyze inputs and intelligently route to appropriate agents
    based on their capabilities and the task requirements.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-5-20250929",
        max_tokens: int = 2000,
    ):
        """
        Initialize AI reasoner.

        Args:
            api_key: Anthropic API key
            model: Claude model to use
            max_tokens: Maximum tokens for response
        """
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.client = AsyncAnthropic(api_key=api_key)

        logger.info(f"AI reasoner initialized with model: {model}")

    def _build_agent_context(self, available_agents: List[BaseAgent]) -> str:
        """
        Build context about available agents for the prompt.

        Args:
            available_agents: List of available agents

        Returns:
            Formatted string describing available agents
        """
        agent_descriptions = []

        for agent in available_agents:
            stats = agent.get_stats()
            description = (
                f"- **{agent.name}**: Capabilities: {', '.join(agent.capabilities)}"
            )
            if agent.metadata.get("description"):
                description += f" - {agent.metadata['description']}"

            agent_descriptions.append(description)

        return "\n".join(agent_descriptions)

    def _build_prompt(
        self,
        input_data: Dict[str, Any],
        available_agents: List[BaseAgent],
    ) -> str:
        """
        Build prompt for Claude.

        Args:
            input_data: Input data to analyze
            available_agents: List of available agents

        Returns:
            Formatted prompt string
        """
        agent_context = self._build_agent_context(available_agents)

        prompt = f"""You are an intelligent agent orchestrator. Your job is to analyze user requests and determine which agents should be called to fulfill the request.

Available Agents:
{agent_context}

User Request:
```json
{json.dumps(input_data, indent=2)}
```

Analyze the request and respond with a JSON object containing:
1. "agents": List of agent names to call (in order if sequential)
2. "reasoning": Explanation of why you selected these agents
3. "confidence": Your confidence score from 0.0 to 1.0
4. "parallel": Boolean - whether agents can be called in parallel
5. "parameters": Optional object with agent-specific parameters {{agent_name: {{param: value}}}}

Guidelines:
- Select only agents whose capabilities match the request
- Prefer fewer agents when possible (don't over-complicate)
- Use parallel execution only if agents are independent
- Provide clear reasoning for your selection
- Be conservative with confidence scores

Respond with ONLY the JSON object, no additional text."""

        return prompt

    async def reason(
        self,
        input_data: Dict[str, Any],
        available_agents: List[BaseAgent],
    ) -> Optional[AgentPlan]:
        """
        Use AI to determine which agents to call.

        Args:
            input_data: Input data to analyze
            available_agents: List of available agents

        Returns:
            AgentPlan with execution plan, or None if reasoning fails
        """
        if not available_agents:
            logger.warning("No available agents for AI reasoning")
            return None

        try:
            logger.info("Using AI reasoner to analyze input")

            prompt = self._build_prompt(input_data, available_agents)

            # Call Claude
            response: Message = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract response text
            response_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    response_text += block.text

            logger.debug(f"AI reasoner response: {response_text}")

            # Parse JSON response
            try:
                # Try to extract JSON from response (handle cases where model adds markdown)
                response_text = response_text.strip()
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.startswith("```"):
                    response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                response_text = response_text.strip()

                plan_data = json.loads(response_text)

                # Validate required fields
                required_fields = ["agents", "reasoning", "confidence"]
                for field in required_fields:
                    if field not in plan_data:
                        logger.error(f"AI response missing required field: {field}")
                        return None

                # Create agent plan
                plan = AgentPlan(
                    agents=plan_data["agents"],
                    reasoning=plan_data["reasoning"],
                    confidence=float(plan_data["confidence"]),
                    parallel=plan_data.get("parallel", False),
                    parameters=plan_data.get("parameters", {}),
                )

                logger.info(f"AI reasoner created plan: {plan}")
                return plan

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                logger.debug(f"Response text: {response_text}")
                return None

        except Exception as e:
            logger.error(f"AI reasoning failed: {e}", exc_info=True)
            return None

    async def validate_plan(
        self,
        plan: AgentPlan,
        available_agents: List[BaseAgent],
    ) -> bool:
        """
        Validate that a plan's agents exist and are healthy.

        Args:
            plan: Agent plan to validate
            available_agents: List of available agents

        Returns:
            True if plan is valid
        """
        available_names = {agent.name for agent in available_agents}

        for agent_name in plan.agents:
            if agent_name not in available_names:
                logger.warning(f"Plan references unknown agent: {agent_name}")
                return False

        return True

    def get_stats(self) -> Dict[str, Any]:
        """
        Get AI reasoner statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
        }
