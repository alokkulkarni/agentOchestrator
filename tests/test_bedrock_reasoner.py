"""
Tests for AWS Bedrock reasoner.

These tests verify the Bedrock reasoner functionality including:
- Client initialization with various credential methods
- AI reasoning using Bedrock Converse API
- Error handling and fallback behavior
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from agent_orchestrator.agents import DirectAgent
from agent_orchestrator.config import DirectToolConfig
from agent_orchestrator.reasoning import BedrockReasoner
from agent_orchestrator.reasoning.ai_reasoner import AgentPlan


@pytest.fixture
def mock_bedrock_client():
    """Mock Bedrock client."""
    client = MagicMock()
    return client


@pytest.fixture
def sample_agents():
    """Create sample agents for testing."""
    return [
        DirectAgent(
            name="calculator",
            capabilities=["math", "calculation"],
            tool_config=DirectToolConfig(
                module="examples.sample_calculator",
                function="calculate",
                is_async=False,
            ),
            metadata={"description": "Performs mathematical calculations"},
        ),
        DirectAgent(
            name="search",
            capabilities=["search", "retrieval"],
            tool_config=DirectToolConfig(
                module="examples.sample_search",
                function="search_documents",
                is_async=True,
            ),
            metadata={"description": "Searches documents"},
        ),
    ]


@pytest.fixture
def mock_bedrock_response():
    """Create mock Bedrock response."""
    return {
        "output": {
            "message": {
                "content": [
                    {
                        "text": json.dumps({
                            "agents": ["calculator"],
                            "reasoning": "The user wants to perform a calculation",
                            "confidence": 0.95,
                            "parallel": False,
                            "parameters": {},
                        })
                    }
                ]
            }
        }
    }


class TestBedrockReasonerInitialization:
    """Test Bedrock reasoner initialization."""

    @patch("agent_orchestrator.reasoning.bedrock_reasoner.boto3")
    def test_init_with_default_credentials(self, mock_boto3):
        """Test initialization with default AWS credentials."""
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        reasoner = BedrockReasoner(
            model_id="anthropic.claude-sonnet-3-5-v2-20241022",
            region="us-east-1",
        )

        assert reasoner.model_id == "anthropic.claude-sonnet-3-5-v2-20241022"
        assert reasoner.region == "us-east-1"
        assert reasoner.role_arn is None
        assert reasoner.aws_profile is None
        mock_boto3.Session.assert_called_once_with()

    @patch("agent_orchestrator.reasoning.bedrock_reasoner.boto3")
    def test_init_with_aws_profile(self, mock_boto3):
        """Test initialization with AWS profile."""
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        reasoner = BedrockReasoner(
            model_id="anthropic.claude-sonnet-3-5-v2-20241022",
            region="us-west-2",
            aws_profile="bedrock-dev",
        )

        assert reasoner.aws_profile == "bedrock-dev"
        mock_boto3.Session.assert_called_once_with(profile_name="bedrock-dev")

    @patch("agent_orchestrator.reasoning.bedrock_reasoner.boto3")
    def test_init_with_sts_assume_role(self, mock_boto3):
        """Test initialization with STS assume role."""
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session

        # Mock STS client
        mock_sts_client = MagicMock()
        mock_sts_client.assume_role.return_value = {
            "Credentials": {
                "AccessKeyId": "test-access-key",
                "SecretAccessKey": "test-secret-key",
                "SessionToken": "test-session-token",
            }
        }

        # Mock Bedrock client
        mock_bedrock_client = MagicMock()

        # Configure session.client to return appropriate mock based on service
        def client_side_effect(service_name, **kwargs):
            if service_name == "sts":
                return mock_sts_client
            elif service_name == "bedrock-runtime":
                return mock_bedrock_client
            return MagicMock()

        mock_session.client.side_effect = client_side_effect

        # Also mock boto3.client for the final bedrock-runtime client creation
        mock_boto3.client.return_value = mock_bedrock_client

        reasoner = BedrockReasoner(
            model_id="anthropic.claude-sonnet-3-5-v2-20241022",
            region="us-east-1",
            role_arn="arn:aws:iam::123456789012:role/BedrockRole",
            session_name="test-session",
        )

        assert reasoner.role_arn == "arn:aws:iam::123456789012:role/BedrockRole"
        mock_sts_client.assume_role.assert_called_once_with(
            RoleArn="arn:aws:iam::123456789012:role/BedrockRole",
            RoleSessionName="test-session",
        )

    @patch("agent_orchestrator.reasoning.bedrock_reasoner.boto3")
    def test_init_no_credentials_error(self, mock_boto3):
        """Test initialization fails when no credentials available."""
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_session.client.side_effect = NoCredentialsError()

        with pytest.raises(NoCredentialsError):
            BedrockReasoner(
                model_id="anthropic.claude-sonnet-3-5-v2-20241022",
                region="us-east-1",
            )

    @patch("agent_orchestrator.reasoning.bedrock_reasoner.boto3")
    def test_init_client_error(self, mock_boto3):
        """Test initialization handles ClientError."""
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_session.client.side_effect = ClientError(
            {"Error": {"Code": "InvalidClientTokenId", "Message": "Invalid token"}},
            "CreateSession"
        )

        with pytest.raises(ClientError):
            BedrockReasoner(
                model_id="anthropic.claude-sonnet-3-5-v2-20241022",
                region="us-east-1",
            )


class TestBedrockReasonerReasoning:
    """Test Bedrock reasoner AI reasoning."""

    @patch("agent_orchestrator.reasoning.bedrock_reasoner.boto3")
    @pytest.mark.asyncio
    async def test_reason_success(
        self,
        mock_boto3,
        sample_agents,
        mock_bedrock_response,
    ):
        """Test successful reasoning with Bedrock."""
        # Setup mocks
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_client.converse.return_value = mock_bedrock_response

        # Create reasoner
        reasoner = BedrockReasoner(
            model_id="anthropic.claude-sonnet-3-5-v2-20241022",
            region="us-east-1",
        )

        # Test reasoning
        input_data = {"query": "calculate 2 plus 2"}
        plan = await reasoner.reason(input_data, sample_agents)

        assert plan is not None
        assert isinstance(plan, AgentPlan)
        assert plan.agents == ["calculator"]
        assert plan.confidence == 0.95
        assert plan.parallel is False
        assert "calculation" in plan.reasoning.lower()

        # Verify Bedrock API was called
        mock_client.converse.assert_called_once()
        call_args = mock_client.converse.call_args
        assert call_args[1]["modelId"] == "anthropic.claude-sonnet-3-5-v2-20241022"
        assert "messages" in call_args[1]

    @patch("agent_orchestrator.reasoning.bedrock_reasoner.boto3")
    @pytest.mark.asyncio
    async def test_reason_with_markdown_json(
        self,
        mock_boto3,
        sample_agents,
    ):
        """Test reasoning handles markdown-wrapped JSON response."""
        # Setup mocks
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        # Response with markdown code block
        mock_response = {
            "output": {
                "message": {
                    "content": [
                        {
                            "text": "```json\n" + json.dumps({
                                "agents": ["search"],
                                "reasoning": "User wants to search",
                                "confidence": 0.88,
                                "parallel": False,
                                "parameters": {},
                            }) + "\n```"
                        }
                    ]
                }
            }
        }
        mock_client.converse.return_value = mock_response

        # Create reasoner
        reasoner = BedrockReasoner()

        # Test reasoning
        input_data = {"query": "search for documents"}
        plan = await reasoner.reason(input_data, sample_agents)

        assert plan is not None
        assert plan.agents == ["search"]
        assert plan.confidence == 0.88

    @patch("agent_orchestrator.reasoning.bedrock_reasoner.boto3")
    @pytest.mark.asyncio
    async def test_reason_no_agents(self, mock_boto3):
        """Test reasoning with no available agents."""
        # Setup mocks
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        # Create reasoner
        reasoner = BedrockReasoner()

        # Test with no agents
        input_data = {"query": "test"}
        plan = await reasoner.reason(input_data, [])

        assert plan is None

    @patch("agent_orchestrator.reasoning.bedrock_reasoner.boto3")
    @pytest.mark.asyncio
    async def test_reason_invalid_json(
        self,
        mock_boto3,
        sample_agents,
    ):
        """Test reasoning handles invalid JSON response."""
        # Setup mocks
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        # Invalid JSON response
        mock_response = {
            "output": {
                "message": {
                    "content": [{"text": "This is not valid JSON"}]
                }
            }
        }
        mock_client.converse.return_value = mock_response

        # Create reasoner
        reasoner = BedrockReasoner()

        # Test reasoning
        input_data = {"query": "test"}
        plan = await reasoner.reason(input_data, sample_agents)

        assert plan is None

    @patch("agent_orchestrator.reasoning.bedrock_reasoner.boto3")
    @pytest.mark.asyncio
    async def test_reason_missing_fields(
        self,
        mock_boto3,
        sample_agents,
    ):
        """Test reasoning handles response with missing required fields."""
        # Setup mocks
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        # Response missing 'confidence' field
        mock_response = {
            "output": {
                "message": {
                    "content": [
                        {
                            "text": json.dumps({
                                "agents": ["calculator"],
                                "reasoning": "Missing confidence",
                                # Missing: confidence
                            })
                        }
                    ]
                }
            }
        }
        mock_client.converse.return_value = mock_response

        # Create reasoner
        reasoner = BedrockReasoner()

        # Test reasoning
        input_data = {"query": "test"}
        plan = await reasoner.reason(input_data, sample_agents)

        assert plan is None

    @patch("agent_orchestrator.reasoning.bedrock_reasoner.boto3")
    @pytest.mark.asyncio
    async def test_reason_bedrock_api_error(
        self,
        mock_boto3,
        sample_agents,
    ):
        """Test reasoning handles Bedrock API errors."""
        # Setup mocks
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        # Simulate API error
        mock_client.converse.side_effect = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
            "Converse"
        )

        # Create reasoner
        reasoner = BedrockReasoner()

        # Test reasoning
        input_data = {"query": "test"}
        plan = await reasoner.reason(input_data, sample_agents)

        assert plan is None

    @patch("agent_orchestrator.reasoning.bedrock_reasoner.boto3")
    @pytest.mark.asyncio
    async def test_reason_with_parallel_execution(
        self,
        mock_boto3,
        sample_agents,
    ):
        """Test reasoning with parallel execution plan."""
        # Setup mocks
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        # Response with parallel execution
        mock_response = {
            "output": {
                "message": {
                    "content": [
                        {
                            "text": json.dumps({
                                "agents": ["calculator", "search"],
                                "reasoning": "Both agents can run in parallel",
                                "confidence": 0.85,
                                "parallel": True,
                                "parameters": {
                                    "calculator": {"precision": 2},
                                    "search": {"max_results": 10},
                                },
                            })
                        }
                    ]
                }
            }
        }
        mock_client.converse.return_value = mock_response

        # Create reasoner
        reasoner = BedrockReasoner()

        # Test reasoning
        input_data = {"query": "calculate and search"}
        plan = await reasoner.reason(input_data, sample_agents)

        assert plan is not None
        assert len(plan.agents) == 2
        assert plan.parallel is True
        assert "calculator" in plan.parameters
        assert "search" in plan.parameters


class TestBedrockReasonerValidation:
    """Test Bedrock reasoner plan validation."""

    @patch("agent_orchestrator.reasoning.bedrock_reasoner.boto3")
    @pytest.mark.asyncio
    async def test_validate_plan_success(self, mock_boto3, sample_agents):
        """Test successful plan validation."""
        # Setup mocks
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        # Create reasoner
        reasoner = BedrockReasoner()

        # Create valid plan
        plan = AgentPlan(
            agents=["calculator"],
            reasoning="Valid plan",
            confidence=0.9,
        )

        # Validate
        is_valid = await reasoner.validate_plan(plan, sample_agents)
        assert is_valid is True

    @patch("agent_orchestrator.reasoning.bedrock_reasoner.boto3")
    @pytest.mark.asyncio
    async def test_validate_plan_unknown_agent(self, mock_boto3, sample_agents):
        """Test plan validation fails for unknown agent."""
        # Setup mocks
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        # Create reasoner
        reasoner = BedrockReasoner()

        # Create plan with unknown agent
        plan = AgentPlan(
            agents=["unknown_agent"],
            reasoning="Invalid plan",
            confidence=0.9,
        )

        # Validate
        is_valid = await reasoner.validate_plan(plan, sample_agents)
        assert is_valid is False


class TestBedrockReasonerStats:
    """Test Bedrock reasoner statistics."""

    @patch("agent_orchestrator.reasoning.bedrock_reasoner.boto3")
    def test_get_stats_no_role(self, mock_boto3):
        """Test stats without STS role."""
        # Setup mocks
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        # Create reasoner
        reasoner = BedrockReasoner(
            model_id="anthropic.claude-sonnet-3-5-v2-20241022",
            region="us-west-2",
        )

        # Get stats
        stats = reasoner.get_stats()

        assert stats["type"] == "bedrock"
        assert stats["model_id"] == "anthropic.claude-sonnet-3-5-v2-20241022"
        assert stats["region"] == "us-west-2"
        assert stats["using_role"] is False
        assert stats["role_arn"] is None

    @patch("agent_orchestrator.reasoning.bedrock_reasoner.boto3")
    def test_get_stats_with_role(self, mock_boto3):
        """Test stats with STS role."""
        # Setup mocks
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session

        # Mock STS client
        mock_sts_client = MagicMock()
        mock_sts_client.assume_role.return_value = {
            "Credentials": {
                "AccessKeyId": "test-key",
                "SecretAccessKey": "test-secret",
                "SessionToken": "test-token",
            }
        }

        # Mock Bedrock client
        mock_bedrock_client = MagicMock()

        def client_side_effect(service_name, **kwargs):
            if service_name == "sts":
                return mock_sts_client
            return MagicMock()

        mock_session.client.side_effect = client_side_effect
        mock_boto3.client.return_value = mock_bedrock_client

        # Create reasoner with role
        reasoner = BedrockReasoner(
            model_id="anthropic.claude-sonnet-3-5-v2-20241022",
            region="us-east-1",
            role_arn="arn:aws:iam::123456789012:role/TestRole",
        )

        # Get stats
        stats = reasoner.get_stats()

        assert stats["using_role"] is True
        assert stats["role_arn"] == "arn:aws:iam::123456789012:role/TestRole"
