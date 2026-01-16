"""
AWS Bedrock-based reasoning engine using Bedrock Converse API for intelligent agent routing.

This module uses AWS Bedrock with Claude models to analyze input and determine
which agents should be called, in what order, and with what parameters.
Supports both AWS credentials from local config and STS assume role.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from ..agents.base_agent import BaseAgent
from .ai_reasoner import AgentPlan

logger = logging.getLogger(__name__)


class BedrockReasoner:
    """
    AWS Bedrock-based reasoning engine using Converse API.

    Uses AWS Bedrock with Claude models to analyze inputs and intelligently route
    to appropriate agents based on their capabilities and the task requirements.

    Supports two authentication modes:
    1. Local AWS credentials (default profile or environment variables)
    2. STS assume role (for cross-account access)
    """

    def __init__(
        self,
        model_id: str = "anthropic.claude-sonnet-3-5-v2-20241022",
        region: str = "us-east-1",
        max_tokens: int = 2000,
        role_arn: Optional[str] = None,
        session_name: str = "agent-orchestrator",
        aws_profile: Optional[str] = None,
    ):
        """
        Initialize Bedrock reasoner.

        Args:
            model_id: Bedrock model ID (e.g., anthropic.claude-sonnet-3-5-v2-20241022)
            region: AWS region for Bedrock
            max_tokens: Maximum tokens for response
            role_arn: Optional IAM role ARN to assume via STS
            session_name: Session name for STS assume role
            aws_profile: Optional AWS profile name to use
        """
        self.model_id = model_id
        self.region = region
        self.max_tokens = max_tokens
        self.role_arn = role_arn
        self.session_name = session_name
        self.aws_profile = aws_profile

        # Initialize Bedrock client
        self.client = self._create_bedrock_client()

        logger.info(
            f"Bedrock reasoner initialized with model: {model_id}, region: {region}"
        )

    def _create_bedrock_client(self):
        """
        Create Bedrock client with appropriate credentials.

        Returns:
            boto3 Bedrock Runtime client

        Raises:
            NoCredentialsError: If AWS credentials cannot be found
            ClientError: If STS assume role fails
        """
        try:
            # Create session with profile if specified
            if self.aws_profile:
                session = boto3.Session(profile_name=self.aws_profile)
                logger.info(f"Using AWS profile: {self.aws_profile}")
            else:
                session = boto3.Session()
                logger.info("Using default AWS credentials")

            # If role ARN provided, assume role via STS
            if self.role_arn:
                logger.info(f"Assuming role: {self.role_arn}")

                sts_client = session.client("sts", region_name=self.region)
                assumed_role = sts_client.assume_role(
                    RoleArn=self.role_arn,
                    RoleSessionName=self.session_name,
                )

                credentials = assumed_role["Credentials"]

                # Create client with assumed role credentials
                client = boto3.client(
                    "bedrock-runtime",
                    region_name=self.region,
                    aws_access_key_id=credentials["AccessKeyId"],
                    aws_secret_access_key=credentials["SecretAccessKey"],
                    aws_session_token=credentials["SessionToken"],
                )

                logger.info("Successfully assumed role and created Bedrock client")
            else:
                # Use default credentials
                client = session.client("bedrock-runtime", region_name=self.region)
                logger.info("Created Bedrock client with default credentials")

            return client

        except NoCredentialsError:
            logger.error(
                "AWS credentials not found. Configure credentials using "
                "AWS CLI, environment variables, or IAM role."
            )
            raise
        except ClientError as e:
            logger.error(f"Failed to create Bedrock client: {e}")
            raise

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
        Build prompt for Bedrock.

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
        Use Bedrock AI to determine which agents to call.

        Args:
            input_data: Input data to analyze
            available_agents: List of available agents

        Returns:
            AgentPlan with execution plan, or None if reasoning fails
        """
        if not available_agents:
            logger.warning("No available agents for Bedrock reasoning")
            return None

        try:
            logger.info("Using Bedrock reasoner to analyze input")

            prompt = self._build_prompt(input_data, available_agents)

            # Call Bedrock Converse API
            response = self.client.converse(
                modelId=self.model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": prompt}],
                    }
                ],
                inferenceConfig={
                    "maxTokens": self.max_tokens,
                    "temperature": 0.0,  # Deterministic for routing
                },
            )

            # Extract response text
            response_text = ""
            if "output" in response and "message" in response["output"]:
                for content_block in response["output"]["message"]["content"]:
                    if "text" in content_block:
                        response_text += content_block["text"]

            logger.debug(f"Bedrock reasoner response: {response_text}")

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
                        logger.error(
                            f"Bedrock response missing required field: {field}"
                        )
                        return None

                # Create agent plan
                plan = AgentPlan(
                    agents=plan_data["agents"],
                    reasoning=plan_data["reasoning"],
                    confidence=float(plan_data["confidence"]),
                    parallel=plan_data.get("parallel", False),
                    parameters=plan_data.get("parameters", {}),
                )

                logger.info(f"Bedrock reasoner created plan: {plan}")
                return plan

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Bedrock response as JSON: {e}")
                logger.debug(f"Response text: {response_text}")
                return None

        except ClientError as e:
            logger.error(f"Bedrock API error: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Bedrock reasoning failed: {e}", exc_info=True)
            return None

    async def validate_plan(
        self,
        plan: AgentPlan,
        available_agents: List[BaseAgent],
    ) -> bool:
        """
        Validate that the agent plan is feasible.

        Args:
            plan: Agent plan to validate
            available_agents: List of available agents

        Returns:
            True if plan is valid, False otherwise
        """
        available_agent_names = {agent.name for agent in available_agents}

        # Check all agents in plan exist
        for agent_name in plan.agents:
            if agent_name not in available_agent_names:
                logger.warning(
                    f"Plan contains unknown agent: {agent_name}. "
                    f"Available: {available_agent_names}"
                )
                return False

        return True

    def get_stats(self) -> Dict[str, Any]:
        """
        Get reasoner statistics.

        Returns:
            Dictionary with reasoner stats
        """
        return {
            "type": "bedrock",
            "model_id": self.model_id,
            "region": self.region,
            "using_role": bool(self.role_arn),
            "role_arn": self.role_arn if self.role_arn else None,
        }
