"""
Gateway-based reasoner for Agent Orchestrator.

Routes requests through the Model Gateway instead of calling providers directly.
Includes comprehensive retry logic and error handling.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import ClientError, ClientTimeout

from .ai_reasoner import AgentPlan
from ..agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class GatewayReasoner:
    """
    Reasoner that uses the Model Gateway for AI decisions.

    Instead of calling Anthropic or Bedrock directly, this reasoner
    makes HTTP requests to the Model Gateway service.
    """

    def __init__(
        self,
        gateway_url: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        max_retries: int = 3,
        timeout: int = 60,
        retry_delay: float = 1.0,
    ):
        """
        Initialize gateway reasoner with retry and error handling.

        Args:
            gateway_url: Base URL of the Model Gateway (e.g., "http://localhost:8000")
            provider: Provider to use (anthropic, bedrock) or None for gateway default
            model: Model identifier or None for provider default
            api_key: Optional API key for gateway authentication
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            max_retries: Maximum retry attempts on failure (default: 3)
            timeout: Request timeout in seconds (default: 60)
            retry_delay: Base delay between retries in seconds (default: 1.0)
        """
        self.gateway_url = gateway_url.rstrip("/")
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.temperature = temperature

        # Retry configuration
        self.max_retries = max_retries
        self.timeout = timeout
        self.retry_delay = retry_delay

        # Error tracking
        self.consecutive_failures = 0
        self.total_requests = 0
        self.total_failures = 0

        logger.info(
            f"Gateway reasoner initialized: url={gateway_url}, "
            f"provider={provider or 'default'}, model={model or 'default'}, "
            f"max_retries={max_retries}, timeout={timeout}s"
        )

    async def reason(
        self,
        query: str,
        agent_capabilities: List,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[AgentPlan]:
        """
        Use AI to reason about which agent(s) to call.

        Args:
            query: User's input query
            agent_capabilities: List of available agents (BaseAgent objects)
            context: Optional context information

        Returns:
            AgentPlan with agent selection or None if failed
        """
        # Build prompt for agent routing
        prompt = self._build_routing_prompt(query, agent_capabilities, context)

        # Create messages
        messages = [{"role": "user", "content": prompt}]

        # Call gateway
        try:
            response = await self._call_gateway(messages)

            # Parse response
            reasoning_text = response["content"]

            # Extract agent selection from response
            plan = self._parse_routing_response(reasoning_text, agent_capabilities)

            if plan:
                logger.info(
                    f"AI reasoning completed: selected {len(plan.agents)} agent(s)"
                )
                return plan
            else:
                logger.warning("AI reasoning returned no agents")
                return None

        except Exception as e:
            logger.error(f"Error during AI reasoning: {e}")
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

    async def validate_output(
        self,
        agent_name: str,
        agent_output: Any,
        expected_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Use AI to validate agent output.

        Args:
            agent_name: Name of the agent
            agent_output: Output from the agent
            expected_schema: Optional expected schema

        Returns:
            Validation result
        """
        # Build validation prompt
        prompt = self._build_validation_prompt(
            agent_name, agent_output, expected_schema
        )

        # Create messages
        messages = [{"role": "user", "content": prompt}]

        # Call gateway
        try:
            response = await self._call_gateway(messages)

            # Parse validation response
            validation_text = response["content"]
            is_valid = "valid" in validation_text.lower()

            return {
                "is_valid": is_valid,
                "validation_message": validation_text,
                "provider": response.get("provider"),
                "model": response.get("model"),
            }

        except Exception as e:
            logger.error(f"Error during AI validation: {e}")
            return {
                "is_valid": False,
                "validation_message": f"Validation failed: {e}",
                "error": str(e),
            }

    async def _call_gateway(
        self, messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Model Gateway with retry logic and error handling.

        Args:
            messages: List of message dicts

        Returns:
            Gateway response

        Raises:
            Exception: After all retries exhausted with detailed error info
        """
        self.total_requests += 1

        # Prepare request
        request_data = {
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        if self.provider:
            request_data["provider"] = self.provider
        if self.model:
            request_data["model"] = self.model

        # Prepare headers
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Gateway endpoint
        url = f"{self.gateway_url}/v1/generate"

        # Configure timeout
        timeout = ClientTimeout(total=self.timeout)

        # Retry loop
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(
                    f"Gateway request attempt {attempt}/{self.max_retries} to {url}"
                )

                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(
                        url, json=request_data, headers=headers
                    ) as response:
                        # Success
                        if response.status == 200:
                            result = await response.json()

                            # Reset failure counter on success
                            self.consecutive_failures = 0

                            logger.debug(
                                f"Gateway request successful (attempt {attempt}/{self.max_retries})"
                            )

                            return result

                        # Handle HTTP errors
                        error_text = await response.text()

                        # Categorize error
                        if response.status == 401:
                            # Authentication error - don't retry
                            error_msg = f"Authentication failed: {error_text[:200]}"
                            logger.error(error_msg)
                            raise Exception(error_msg)

                        elif response.status == 400:
                            # Bad request - don't retry
                            error_msg = f"Bad request: {error_text[:200]}"
                            logger.error(error_msg)
                            raise Exception(error_msg)

                        elif response.status == 404:
                            # Not found - don't retry
                            error_msg = f"Gateway endpoint not found: {url}"
                            logger.error(error_msg)
                            raise Exception(error_msg)

                        elif response.status == 429:
                            # Rate limit - retry with longer delay
                            error_msg = f"Rate limited (attempt {attempt}/{self.max_retries})"
                            logger.warning(error_msg)
                            last_error = Exception(f"Rate limit exceeded: {error_text[:200]}")

                            # Wait longer for rate limits
                            if attempt < self.max_retries:
                                delay = self.retry_delay * (2 ** (attempt - 1)) * 2
                                logger.info(f"Waiting {delay:.1f}s before retry due to rate limit")
                                await asyncio.sleep(delay)
                            continue

                        elif response.status >= 500:
                            # Server error - retry
                            error_msg = f"Gateway server error {response.status} (attempt {attempt}/{self.max_retries})"
                            logger.warning(error_msg)
                            last_error = Exception(f"Server error: {error_text[:200]}")

                            if attempt < self.max_retries:
                                delay = self.retry_delay * (2 ** (attempt - 1))
                                logger.info(f"Retrying in {delay:.1f}s...")
                                await asyncio.sleep(delay)
                            continue

                        else:
                            # Other error - retry
                            error_msg = f"Gateway error {response.status} (attempt {attempt}/{self.max_retries}): {error_text[:200]}"
                            logger.warning(error_msg)
                            last_error = Exception(error_msg)

                            if attempt < self.max_retries:
                                delay = self.retry_delay * (2 ** (attempt - 1))
                                await asyncio.sleep(delay)
                            continue

            except asyncio.TimeoutError as e:
                # Timeout - retry
                error_msg = f"Gateway request timeout after {self.timeout}s (attempt {attempt}/{self.max_retries})"
                logger.warning(error_msg)
                last_error = e

                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    logger.info(f"Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                continue

            except (aiohttp.ClientConnectorError, aiohttp.ClientConnectionError) as e:
                # Connection error - retry
                error_msg = f"Gateway connection error (attempt {attempt}/{self.max_retries}): {str(e)[:200]}"
                logger.warning(error_msg)
                last_error = e

                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    logger.info(f"Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                continue

            except ClientError as e:
                # Other client errors - retry
                error_msg = f"Gateway client error (attempt {attempt}/{self.max_retries}): {str(e)[:200]}"
                logger.warning(error_msg)
                last_error = e

                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)
                continue

            except Exception as e:
                # Unexpected error
                error_msg = f"Unexpected error calling gateway (attempt {attempt}/{self.max_retries}): {str(e)[:200]}"
                logger.error(error_msg)
                last_error = e

                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)
                continue

        # All retries exhausted
        self.consecutive_failures += 1
        self.total_failures += 1

        error_summary = (
            f"Gateway request failed after {self.max_retries} attempts. "
            f"URL: {url}, "
            f"Consecutive failures: {self.consecutive_failures}, "
            f"Total failures: {self.total_failures}/{self.total_requests}. "
            f"Last error: {str(last_error)[:300]}"
        )

        logger.error(error_summary)
        raise Exception(error_summary)

    def _build_routing_prompt(
        self,
        query: str,
        agent_capabilities: List,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build prompt for agent routing decision."""
        prompt = f"""You are an agent orchestration system. Your job is to analyze the user's query and determine which agent(s) should handle it.

User Query: {query}

Available Agents:
"""
        for idx, agent in enumerate(agent_capabilities, 1):
            name = agent.name
            capabilities = agent.capabilities
            prompt += f"{idx}. {name}: {', '.join(capabilities)}\n"

        if context:
            prompt += f"\nContext: {context}\n"

        prompt += """
Based on the query and available agents, respond with:
1. Which agent(s) should be called (you CAN call same agent multiple times)
2. Whether they should run in parallel or sequential
3. Brief reasoning for your choice
4. Agent-specific parameters extracted from the query

IMPORTANT - Multi-Instance Support:
  - You CAN call the same agent multiple times with different parameters
  - For multiple calls, use numbered suffixes: agent_1, agent_2, etc.
  - Example: For "weather in Paris and London":
    AGENTS: weather, weather
    PARAMETERS: {"weather_1": {"location": "Paris"}, "weather_2": {"location": "London"}}

Parameter Extraction Guidelines:
  For calculator agent - REQUIRED FORMAT:
    - "operation": Use EXACT values: "add", "subtract", "multiply", "divide", "average", "power", "sqrt"
    - "operands": MUST be a list of numbers [num1, num2, ...], OR
    - "data_source": "previous" to use data from earlier agents
    - "field": Field to extract (e.g., "temp" for temperature)
    Examples:
      "25 + 75" → {"operation": "add", "operands": [25, 75]}
      "average temperature from previous results" → {"operation": "average", "data_source": "previous", "field": "temp"}

  For weather agent:
    - "location": City/location name as string
    Example: "weather in Paris" → {"location": "Paris"}

  For search agents:
    - "keywords": List of search terms
    Example: "search for AI" → {"keywords": ["AI"]}

Data Chaining Example:
  Query: "weather in Paris and London, calculate average"
  AGENTS: weather, weather, calculator
  MODE: sequential
  PARAMETERS: {
    "weather_1": {"location": "Paris"},
    "weather_2": {"location": "London"},
    "calculator": {"operation": "average", "data_source": "previous", "field": "temp"}
  }

Format your response as:
AGENTS: [agent names separated by commas]
MODE: [parallel or sequential]
REASONING: [your reasoning]
PARAMETERS: {"agent_name": {"param": value}, ...} (as JSON, MUST match exact format above)
"""
        return prompt

    def _build_validation_prompt(
        self,
        agent_name: str,
        agent_output: Any,
        expected_schema: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build prompt for output validation."""
        prompt = f"""You are validating the output from an agent.

Agent: {agent_name}
Output: {agent_output}
"""

        if expected_schema:
            prompt += f"\nExpected Schema: {expected_schema}\n"

        prompt += """
Determine if the output is valid and meets expectations.
Respond with either:
- VALID: [explanation]
- INVALID: [explanation of what's wrong]
"""
        return prompt

    async def validate_rule_selection(
        self,
        input_data: Dict[str, Any],
        rule_selected_agents: List[str],
        available_agents: List[Any],
        rule_name: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Validate rule-based agent selection using AI via gateway.

        Args:
            input_data: Original input data
            rule_selected_agents: Agents selected by rule engine
            available_agents: List of available agents
            rule_name: Name of the rule that matched

        Returns:
            Dictionary with validation result
        """
        # Build agent context
        agent_context = ""
        for agent in available_agents:
            name = agent.name if hasattr(agent, "name") else str(agent)
            caps = agent.capabilities if hasattr(agent, "capabilities") else []
            agent_context += f"- {name}: {', '.join(caps)}\n"

        # Build validation prompt
        prompt = f"""You are an AI agent router validator. A rule-based system has selected agents to handle a user request.
Your job is to validate if these agents are appropriate, extract parameters for each agent, or suggest better agents if needed.

Available Agents:
{agent_context}

User Request:
{input_data}

Rule-Based Selection:
- Rule: {rule_name}
- Selected Agents: {', '.join(rule_selected_agents)}

Task:
1. Analyze if the selected agents are appropriate for this request
2. Extract specific parameters needed for each agent from the user request
3. If the selection is good, validate it
4. If not appropriate, suggest which agents should be used instead

IMPORTANT - Multi-Instance Support:
- You CAN suggest calling the same agent multiple times with different parameters
- For multiple calls, list the agent name multiple times in suggested_agents array
- Use numbered suffixes in parameters (e.g., weather_1, weather_2, weather_3)

Example for "weather in Paris, London, and Berlin":
{{
    "is_valid": false,
    "confidence": 0.9,
    "reasoning": "Need to call weather agent three times for three cities",
    "suggested_agents": ["weather", "weather", "weather"],
    "parameters": {{
        "weather_1": {{"location": "Paris"}},
        "weather_2": {{"location": "London"}},
        "weather_3": {{"location": "Berlin"}}
    }}
}}

For data chaining (when one agent needs output from previous agents):
- Use "data_source": "previous" in parameters
- Specify field to extract with "field": "temp"
- Example: {{"calculator": {{"operation": "average", "data_source": "previous", "field": "temp"}}}}

Respond in JSON format:
{{
    "is_valid": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "explanation",
    "suggested_agents": ["agent1", "agent1", "agent2"] (can include duplicates),
    "parameters": {{"agent_name_1": {{"param": "value"}}, "agent_name_2": {{"param": "value"}}}}
}}"""

        # Create messages
        messages = [{"role": "user", "content": prompt}]

        try:
            # Call gateway
            response = await self._call_gateway(messages)
            response_text = response["content"]

            # Parse JSON response
            import json
            import re

            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without code blocks
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                json_str = json_match.group(0) if json_match else response_text

            result = json.loads(json_str)

            # Normalize calculator parameters to expected format
            if "parameters" in result:
                result["parameters"] = self._normalize_calculator_parameters(result["parameters"])
                logger.info(f"Normalized parameters in validation: {result['parameters']}")

            return result

        except Exception as e:
            logger.error(f"Error during rule validation: {e}")
            # Return a safe default that approves the rule selection
            return {
                "is_valid": True,
                "confidence": 0.5,
                "reasoning": f"Validation failed, accepting rule selection: {e}",
                "suggested_agents": [],
                "parameters": {},
            }

    def _normalize_calculator_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize calculator parameters to the expected format.

        Handles AI variations like:
        - "division" -> "divide", "multiplication" -> "multiply", etc.
        - {"operand1": 100, "operand2": 4} -> {"operands": [100, 4]}
        - Removes extra fields like "expression"
        """
        if "calculator" not in parameters:
            return parameters

        calc_params = parameters["calculator"]
        normalized = {}

        # Normalize operation names
        operation = calc_params.get("operation", "")
        operation_map = {
            "addition": "add",
            "sum": "add",
            "plus": "add",
            "subtraction": "subtract",
            "minus": "subtract",
            "difference": "subtract",
            "multiplication": "multiply",
            "times": "multiply",
            "product": "multiply",
            "division": "divide",
            "div": "divide",
            "divided": "divide",
        }
        normalized["operation"] = operation_map.get(operation.lower(), operation)

        # Normalize operands - convert from operand1, operand2, etc. to list
        if "operands" in calc_params:
            # Already in correct format
            normalized["operands"] = calc_params["operands"]
        elif "operand1" in calc_params and "operand2" in calc_params:
            # Convert operand1, operand2 to list
            operands = [calc_params["operand1"], calc_params["operand2"]]
            # Add any additional operands
            i = 3
            while f"operand{i}" in calc_params:
                operands.append(calc_params[f"operand{i}"])
                i += 1
            normalized["operands"] = operands
        elif "numbers" in calc_params:
            # Alternative format
            normalized["operands"] = calc_params["numbers"]

        # If calculator has operation but no operands, assume it needs data from previous agents
        if "operation" in normalized and "operands" not in normalized:
            if normalized["operation"] in ["average", "avg", "mean", "sum", "add"]:
                # These operations typically need data from previous responses
                normalized["data_source"] = "previous"
                normalized["field"] = "temp"  # Default to temperature for weather
                logger.info(f"Auto-added data chaining for calculator: {normalized['operation']}")

        parameters["calculator"] = normalized
        logger.info(f"Normalized calculator parameters: {normalized}")
        return parameters

    def _parse_routing_response(
        self, response_text: str, agent_capabilities: List
    ) -> Optional[AgentPlan]:
        """Parse AI routing response into an AgentPlan."""
        import json
        import re

        agents = []
        parallel = False
        reasoning = response_text
        parameters = {}

        # Extract agents
        if "AGENTS:" in response_text:
            agents_line = response_text.split("AGENTS:")[1].split("\n")[0].strip()
            agent_names = [a.strip() for a in agents_line.split(",")]

            # Match to actual agent objects
            for name in agent_names:
                for agent in agent_capabilities:
                    if agent.name.lower() == name.lower():
                        agents.append(agent.name)
                        break

        # Extract mode
        if "MODE:" in response_text:
            mode_line = response_text.split("MODE:")[1].split("\n")[0].strip().lower()
            if "parallel" in mode_line:
                parallel = True

        # Extract reasoning
        if "REASONING:" in response_text:
            reasoning_section = response_text.split("REASONING:")[1]
            # Stop at PARAMETERS if it exists
            if "PARAMETERS:" in reasoning_section:
                reasoning = reasoning_section.split("PARAMETERS:")[0].strip()
            else:
                reasoning = reasoning_section.strip()

        # Extract parameters
        if "PARAMETERS:" in response_text:
            params_section = response_text.split("PARAMETERS:")[1].strip()
            try:
                # Try to parse as JSON
                # Handle both single-line and multi-line JSON
                json_match = re.search(r'\{.*\}', params_section, re.DOTALL)
                if json_match:
                    params_str = json_match.group(0)
                    parameters = json.loads(params_str)
                    logger.info(f"Extracted parameters: {parameters}")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse PARAMETERS as JSON: {e}")
                # Continue without parameters

        # Return AgentPlan if we have agents
        if agents:
            return AgentPlan(
                agents=agents,
                reasoning=reasoning,
                confidence=0.8,  # Default confidence for gateway reasoner
                parallel=parallel,
                parameters=parameters,
            )

        return None

    def get_stats(self) -> Dict[str, Any]:
        """
        Get gateway reasoner statistics.

        Returns:
            Dictionary with statistics including retry stats
        """
        stats = {
            "gateway_url": self.gateway_url,
            "provider": self.provider or "default",
            "model": self.model or "default",
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "retry_delay": self.retry_delay,
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "consecutive_failures": self.consecutive_failures,
        }

        # Add success rate if there have been requests
        if self.total_requests > 0:
            stats["success_rate"] = (
                (self.total_requests - self.total_failures) / self.total_requests
            )
        else:
            stats["success_rate"] = 0.0

        return stats
