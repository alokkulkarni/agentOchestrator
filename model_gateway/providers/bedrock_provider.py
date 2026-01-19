"""
AWS Bedrock provider adapter for Model Gateway.

Handles communication with AWS Bedrock Converse API.
"""

import time
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from .base_provider import BaseProvider


class BedrockProvider(BaseProvider):
    """AWS Bedrock Converse API provider."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Bedrock provider.

        Args:
            config: Configuration dict with:
                - region: AWS region (e.g., "us-east-1")
                - model_id: Bedrock model ID or inference profile ARN
                - aws_profile: Optional AWS profile name
                - role_arn: Optional IAM role ARN for assume role
                - session_name: Session name for STS (if using role_arn)
        """
        super().__init__(config)
        self.region = config.get("region", "us-east-1")
        self.model_id = config.get(
            "model_id", "anthropic.claude-sonnet-3-5-v2-20241022"
        )
        self.aws_profile = config.get("aws_profile")
        self.role_arn = config.get("role_arn")
        self.session_name = config.get("session_name", "model-gateway")

        # Initialize Bedrock client
        self.client = self._create_client()

    def _create_client(self):
        """Create Bedrock runtime client with appropriate credentials."""
        # Start with session configuration
        session_kwargs = {}
        if self.aws_profile:
            session_kwargs["profile_name"] = self.aws_profile

        session = boto3.Session(**session_kwargs)

        # If role_arn is provided, assume that role
        if self.role_arn:
            sts_client = session.client("sts", region_name=self.region)
            assumed_role = sts_client.assume_role(
                RoleArn=self.role_arn, RoleSessionName=self.session_name
            )

            credentials = assumed_role["Credentials"]
            client = boto3.client(
                "bedrock-runtime",
                region_name=self.region,
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
            )
        else:
            # Use default credentials or profile
            client = session.client("bedrock-runtime", region_name=self.region)

        return client

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a response using AWS Bedrock Converse API.

        Args:
            messages: List of message dicts
            model: Model ID or inference profile ARN
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            Standardized response dict
        """
        model = model or self.model_id

        # Convert messages to Bedrock format
        bedrock_messages = self._convert_messages(messages)

        try:
            # Call Bedrock Converse API
            response = self.client.converse(
                modelId=model,
                messages=bedrock_messages,
                inferenceConfig={
                    "maxTokens": max_tokens,
                    "temperature": temperature,
                },
            )

            # Extract content
            content = ""
            if "output" in response and "message" in response["output"]:
                message = response["output"]["message"]
                if "content" in message:
                    for block in message["content"]:
                        if "text" in block:
                            content += block["text"]

            # Extract usage
            usage = response.get("usage", {})
            input_tokens = usage.get("inputTokens", 0)
            output_tokens = usage.get("outputTokens", 0)

            # Get stop reason
            stop_reason = response.get("stopReason", "end_turn")

            # Standardize response
            return self.standardize_response(
                content=content,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                finish_reason=stop_reason,
            )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get(
                "Message", str(e)
            )
            raise Exception(f"Bedrock API error ({error_code}): {error_message}")
        except BotoCoreError as e:
            raise Exception(f"Bedrock connection error: {str(e)}")
        except Exception as e:
            raise Exception(f"Error calling Bedrock: {str(e)}")

    async def health_check(self) -> Dict[str, Any]:
        """
        Check Bedrock API health.

        Returns:
            Health status dict
        """
        start_time = time.time()
        try:
            # Make a minimal API call to check health
            response = self.client.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": "ping"}]}],
                inferenceConfig={"maxTokens": 10, "temperature": 0.0},
            )

            latency_ms = (time.time() - start_time) * 1000

            return {
                "status": "healthy",
                "provider": "BedrockProvider",
                "latency_ms": round(latency_ms, 2),
                "model": self.model_id,
                "region": self.region,
                "error": None,
            }

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return {
                "status": "unhealthy",
                "provider": "BedrockProvider",
                "latency_ms": round(latency_ms, 2),
                "error": str(e),
            }

    def _convert_messages(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert standard messages to Bedrock Converse format.

        Args:
            messages: Standard message format

        Returns:
            Bedrock-formatted messages
        """
        bedrock_messages = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Bedrock Converse uses "user" and "assistant" roles
            if role in ["user", "assistant"]:
                bedrock_messages.append(
                    {"role": role, "content": [{"text": content}]}
                )
            elif role == "system":
                # System messages prepended to first user message
                if bedrock_messages and bedrock_messages[0]["role"] == "user":
                    bedrock_messages[0]["content"][0]["text"] = (
                        f"{content}\n\n{bedrock_messages[0]['content'][0]['text']}"
                    )
                else:
                    bedrock_messages.insert(
                        0, {"role": "user", "content": [{"text": content}]}
                    )

        return bedrock_messages

    def get_model_info(self) -> Dict[str, Any]:
        """Get Bedrock model information."""
        return {
            "provider": "BedrockProvider",
            "models": [
                "anthropic.claude-sonnet-3-5-v2-20241022",
                "anthropic.claude-3-5-sonnet-20240620-v1:0",
                "anthropic.claude-3-opus-20240229-v1:0",
                "anthropic.claude-3-sonnet-20240229-v1:0",
                "anthropic.claude-3-haiku-20240307-v1:0",
            ],
            "default_model": self.model_id,
            "region": self.region,
        }
