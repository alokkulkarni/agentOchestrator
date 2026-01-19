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
        agent_capabilities: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Use AI to reason about which agent(s) to call.

        Args:
            query: User's input query
            agent_capabilities: List of available agents and their capabilities
            context: Optional context information

        Returns:
            Reasoning result with agent selection
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
            result = self._parse_routing_response(reasoning_text, agent_capabilities)

            logger.info(
                f"AI reasoning completed: selected {len(result.get('agents', []))} agent(s)"
            )

            return result

        except Exception as e:
            logger.error(f"Error during AI reasoning: {e}")
            return {
                "success": False,
                "error": str(e),
                "agents": [],
                "reasoning": f"Failed to reason: {e}",
            }

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
        agent_capabilities: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build prompt for agent routing decision."""
        prompt = f"""You are an agent orchestration system. Your job is to analyze the user's query and determine which agent(s) should handle it.

User Query: {query}

Available Agents:
"""
        for idx, agent in enumerate(agent_capabilities, 1):
            name = agent.get("name", "unknown")
            capabilities = agent.get("capabilities", [])
            prompt += f"{idx}. {name}: {', '.join(capabilities)}\n"

        if context:
            prompt += f"\nContext: {context}\n"

        prompt += """
Based on the query and available agents, respond with:
1. Which agent(s) should be called
2. Whether they should run in parallel or sequential
3. Brief reasoning for your choice

Format your response as:
AGENTS: [agent names separated by commas]
MODE: [parallel or sequential]
REASONING: [your reasoning]
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

Respond in JSON format:
{{
    "is_valid": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "explanation",
    "suggested_agents": ["agent1"] (only if is_valid is false),
    "parameters": {{"agent_name": {{"param": "value"}}}}
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

    def _parse_routing_response(
        self, response_text: str, agent_capabilities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Parse AI routing response into structured format."""
        agents = []
        mode = "sequential"
        reasoning = response_text

        # Extract agents
        if "AGENTS:" in response_text:
            agents_line = response_text.split("AGENTS:")[1].split("\n")[0].strip()
            agent_names = [a.strip() for a in agents_line.split(",")]

            # Match to actual agent objects
            for name in agent_names:
                for agent in agent_capabilities:
                    if agent.get("name", "").lower() == name.lower():
                        agents.append(agent)
                        break

        # Extract mode
        if "MODE:" in response_text:
            mode_line = response_text.split("MODE:")[1].split("\n")[0].strip().lower()
            if "parallel" in mode_line:
                mode = "parallel"
            else:
                mode = "sequential"

        # Extract reasoning
        if "REASONING:" in response_text:
            reasoning = response_text.split("REASONING:")[1].strip()

        return {
            "success": True,
            "agents": agents,
            "mode": mode,
            "reasoning": reasoning,
        }

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
