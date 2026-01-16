"""
Main orchestrator class for agent coordination.

This module provides the core Orchestrator class that ties together all components:
- Agent registry and management
- Reasoning engines (rule-based, AI, hybrid)
- Output validation and formatting
- Retry and fallback logic
- Security validation
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .agents import AgentRegistry, DirectAgent, MCPAgent
from .config import (
    AgentConfig,
    AgentType,
    ConfigurationError,
    load_all_configs,
    OrchestratorConfig,
)
from .reasoning import AIReasoner, BedrockReasoner, HybridReasoner, RuleEngine
from .utils import (
    CircuitBreaker,
    FallbackStrategy,
    QueryLogger,
    RetryHandler,
    SecurityError,
    setup_logging,
    validate_input,
)
from .validation import OutputFormatter, ResponseValidator, SchemaValidator

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Main agent orchestrator class.

    Coordinates multiple agents using intelligent reasoning to route requests,
    validate outputs, handle failures, and format results.
    """

    def __init__(
        self,
        config_path: str = "config/orchestrator.yaml",
        api_key: Optional[str] = None,
    ):
        """
        Initialize orchestrator from configuration.

        Args:
            config_path: Path to orchestrator configuration file
            api_key: Optional Anthropic API key (overrides env var, only used for Anthropic provider)

        Note:
            - For Anthropic provider: Requires ANTHROPIC_API_KEY environment variable or api_key parameter
            - For Bedrock provider: Uses AWS credentials from environment, profile, or STS assume role
        """
        self.config_path = config_path
        self._initialized = False
        self._request_count = 0

        # Load configuration
        logger.info(f"Loading orchestrator configuration from {config_path}")
        try:
            self.config, self.agents_config, self.rules_config = load_all_configs(config_path)
        except ConfigurationError as e:
            logger.error(f"Configuration error: {e}")
            raise

        # Setup logging
        setup_logging(level=self.config.log_level)

        # Initialize components
        self.agent_registry = AgentRegistry()
        self.rule_engine = RuleEngine(self.rules_config)

        # Initialize AI reasoner based on provider
        self.ai_reasoner = None
        if self.config.reasoning_mode in ["ai", "hybrid"]:
            if self.config.ai_provider == "anthropic":
                # Anthropic provider
                self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
                if not self.api_key:
                    raise ConfigurationError(
                        "ANTHROPIC_API_KEY not found and required for Anthropic AI reasoning"
                    )

                self.ai_reasoner = AIReasoner(
                    api_key=self.api_key,
                    model=self.config.ai_model,
                )
                logger.info(f"Initialized Anthropic AI reasoner with model: {self.config.ai_model}")

            elif self.config.ai_provider == "bedrock":
                # AWS Bedrock provider
                if not self.config.bedrock:
                    raise ConfigurationError(
                        "Bedrock configuration required when ai_provider is 'bedrock'"
                    )

                self.ai_reasoner = BedrockReasoner(
                    model_id=self.config.bedrock.model_id,
                    region=self.config.bedrock.region,
                    role_arn=self.config.bedrock.role_arn,
                    session_name=self.config.bedrock.session_name,
                    aws_profile=self.config.bedrock.aws_profile,
                )
                logger.info(
                    f"Initialized Bedrock AI reasoner with model: {self.config.bedrock.model_id}, "
                    f"region: {self.config.bedrock.region}"
                )
            else:
                raise ConfigurationError(
                    f"Invalid ai_provider: {self.config.ai_provider}. Must be 'anthropic' or 'bedrock'"
                )

        self.hybrid_reasoner = None
        if self.config.reasoning_mode == "hybrid" and self.ai_reasoner:
            self.hybrid_reasoner = HybridReasoner(
                rule_engine=self.rule_engine,
                ai_reasoner=self.ai_reasoner,
                mode=self.config.reasoning_mode,
            )

        # Initialize utilities
        self.fallback_strategy = FallbackStrategy(self.agent_registry)
        self.retry_handler = RetryHandler(
            retry_config=self.config.retry_config,
            fallback_strategy=self.fallback_strategy,
        )
        self.circuit_breaker = CircuitBreaker()

        # Initialize validation and formatting
        schemas_path = os.path.join(
            os.path.dirname(config_path),
            self.config.schemas_path
        )
        self.schema_validator = SchemaValidator(schemas_path)
        self.output_formatter = OutputFormatter(
            include_metadata=self.config.enable_metrics,
        )

        # Initialize response validator
        self.response_validator = ResponseValidator(
            anthropic_api_key=self.api_key if hasattr(self, 'api_key') else None,
            enable_ai_validation=self.config.reasoning_mode in ["ai", "hybrid"],
            confidence_threshold=getattr(self.config, 'validation_confidence_threshold', 0.7),
        )

        # Initialize query logger
        self.query_logger = QueryLogger(
            log_dir=getattr(self.config, 'query_log_dir', 'logs/queries'),
            log_to_file=getattr(self.config, 'log_queries_to_file', True),
            log_to_console=getattr(self.config, 'log_queries_to_console', False),
        )

        # Execution context
        self._execution_history: List[Dict[str, Any]] = []

        logger.info(f"Orchestrator initialized: {self.config.name}")

    async def initialize(self) -> None:
        """
        Initialize orchestrator by loading and registering all agents.

        Must be called before processing requests.
        """
        if self._initialized:
            logger.warning("Orchestrator already initialized")
            return

        logger.info("Initializing orchestrator and loading agents")

        # Load and register agents from configuration
        for agent_config in self.agents_config.agents:
            if not agent_config.enabled:
                logger.info(f"Skipping disabled agent: {agent_config.name}")
                continue

            try:
                agent = self._create_agent(agent_config)
                await self.agent_registry.register(agent, initialize=True)
                logger.info(f"Registered agent: {agent_config.name}")
            except Exception as e:
                logger.error(f"Failed to register agent {agent_config.name}: {e}")
                # Continue with other agents

        self._initialized = True
        logger.info(
            f"Orchestrator initialization complete: "
            f"{self.agent_registry.count()} agents registered"
        )

    def _create_agent(self, config: AgentConfig):
        """
        Create agent instance from configuration.

        Args:
            config: Agent configuration

        Returns:
            Agent instance (MCPAgent or DirectAgent)
        """
        if config.type == AgentType.MCP:
            if not config.connection:
                raise ConfigurationError(f"MCP agent {config.name} missing connection config")

            return MCPAgent(
                name=config.name,
                capabilities=config.capabilities,
                connection_config=config.connection,
                metadata=config.metadata,
            )
        elif config.type == AgentType.DIRECT:
            if not config.direct_tool:
                raise ConfigurationError(f"Direct agent {config.name} missing direct_tool config")

            return DirectAgent(
                name=config.name,
                capabilities=config.capabilities,
                tool_config=config.direct_tool,
                metadata=config.metadata,
            )
        else:
            raise ConfigurationError(f"Unknown agent type: {config.type}")

    async def process(
        self,
        input_data: Dict[str, Any],
        validate_input_security: bool = True,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process input through the orchestrator.

        Main entry point for orchestrating agent calls with:
        - Response validation against user query
        - Hallucination detection
        - Confidence scoring (logged, not sent to user)
        - Retry on validation failure
        - Comprehensive per-query logging

        Args:
            input_data: Input data to process
            validate_input_security: Whether to validate input for security issues
            request_id: Optional request ID for tracking

        Returns:
            Formatted output dictionary with results
        """
        if not self._initialized:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")

        # Generate request ID if not provided
        request_id = request_id or str(uuid.uuid4())
        start_time = datetime.utcnow()

        logger.info(f"Processing request {request_id}")
        self._request_count += 1

        # Create query logging context
        query_context = self.query_logger.create_query_context(input_data)

        try:
            # Step 1: Security validation
            if validate_input_security:
                try:
                    validate_input(input_data)
                except SecurityError as e:
                    error_msg = f"Security validation failed: {e}"
                    logger.error(error_msg)
                    self.query_logger.log_error(
                        query_context,
                        error_type="SecurityError",
                        error_message=error_msg,
                    )
                    output = self.output_formatter.create_error_output(
                        error_message=error_msg,
                        request_id=request_id,
                    )
                    self.query_logger.finalize_query_log(query_context, output)
                    return output

            # Step 2: Reasoning - determine which agents to call
            reasoning_result = await self._reason(input_data)
            if not reasoning_result:
                error_msg = "No agents could be determined for this request"
                self.query_logger.log_error(
                    query_context,
                    error_type="ReasoningError",
                    error_message=error_msg,
                )
                output = self.output_formatter.create_error_output(
                    error_message=error_msg,
                    request_id=request_id,
                )
                self.query_logger.finalize_query_log(query_context, output)
                return output

            # Log reasoning decision
            self.query_logger.log_reasoning(
                query_context,
                reasoning_mode=self.config.reasoning_mode,
                reasoning_result={
                    "agents": reasoning_result.agents,
                    "confidence": reasoning_result.confidence,
                    "method": reasoning_result.method,
                    "reasoning": reasoning_result.reasoning,
                    "parallel": reasoning_result.parallel,
                    "parameters": reasoning_result.parameters,
                },
            )

            logger.info(
                f"Reasoning complete: {len(reasoning_result.agents)} agent(s) selected "
                f"(method={reasoning_result.method}, confidence={reasoning_result.confidence:.2f})"
            )

            # Step 3: Execute agents with validation and retry
            max_retries = getattr(self.config, 'validation_max_retries', 2)
            output = await self._execute_and_validate(
                query_context=query_context,
                input_data=input_data,
                reasoning_result=reasoning_result,
                request_id=request_id,
                max_retries=max_retries,
            )

            # Step 4: Record execution history
            if self.config.enable_audit_log:
                self._record_execution(
                    request_id=request_id,
                    input_data=input_data,
                    reasoning_result=reasoning_result,
                    agent_responses=[],  # Not available in new flow
                    output=output,
                    start_time=start_time,
                )

            # Finalize query log
            self.query_logger.finalize_query_log(query_context, output)

            logger.info(f"Request {request_id} completed successfully")
            return output

        except Exception as e:
            logger.error(f"Error processing request {request_id}: {e}", exc_info=True)
            self.query_logger.log_error(
                query_context,
                error_type=type(e).__name__,
                error_message=str(e),
                error_details={"traceback": str(e)},
            )
            output = self.output_formatter.create_error_output(
                error_message=f"Orchestration error: {str(e)}",
                request_id=request_id,
            )
            self.query_logger.finalize_query_log(query_context, output)
            return output

    async def _reason(self, input_data: Dict[str, Any]):
        """Determine which agents to call using configured reasoning mode."""
        available_agents = self.agent_registry.get_all()

        # Filter out agents with open circuit breakers
        available_agents = [
            agent for agent in available_agents
            if not self.circuit_breaker.is_open(agent.name)
        ]

        if not available_agents:
            logger.error("No available agents (all circuit breakers open)")
            return None

        # Use appropriate reasoning method
        if self.config.reasoning_mode == "rule":
            return self.hybrid_reasoner._rule_only(input_data, available_agents)
        elif self.config.reasoning_mode == "ai" and self.ai_reasoner:
            return await self.hybrid_reasoner._ai_only(input_data, available_agents)
        elif self.config.reasoning_mode == "hybrid" and self.hybrid_reasoner:
            return await self.hybrid_reasoner.reason(input_data, available_agents)
        else:
            logger.error(f"Invalid reasoning mode: {self.config.reasoning_mode}")
            return None

    async def _execute_agents(
        self,
        agent_names: List[str],
        input_data: Dict[str, Any],
        parallel: bool,
        parameters: Dict[str, Dict[str, Any]],
    ):
        """Execute the selected agents with retry and fallback logic."""
        agents = []
        fallback_map = {}

        for agent_name in agent_names:
            agent = self.agent_registry.get(agent_name)
            if not agent:
                logger.warning(f"Agent {agent_name} not found in registry")
                continue

            agents.append(agent)

            # Get fallback agent from configuration
            agent_config = self.agents_config.get_agent(agent_name)
            if agent_config and agent_config.fallback:
                fallback_map[agent_name] = agent_config.fallback

        if not agents:
            logger.error("No valid agents found for execution")
            return []

        # Prepare input data with agent-specific parameters
        def get_agent_input(agent_name: str) -> Dict[str, Any]:
            agent_params = parameters.get(agent_name, {})
            return {**input_data, **agent_params}

        # Execute with retry handler
        if parallel:
            # Call agents in parallel
            responses = await self.retry_handler.call_multiple_with_retry(
                agents=agents,
                input_data=input_data,
                timeout=self.config.default_timeout,
                fallback_map=fallback_map,
                parallel=True,
            )
        else:
            # Call agents sequentially
            responses = []
            for agent in agents:
                agent_input = get_agent_input(agent.name)
                response = await self.retry_handler.call_with_retry(
                    agent=agent,
                    input_data=agent_input,
                    timeout=self.config.default_timeout,
                    fallback_agent_name=fallback_map.get(agent.name),
                )
                responses.append(response)

                # Update circuit breaker
                if response.success:
                    self.circuit_breaker.record_success(agent.name)
                else:
                    self.circuit_breaker.record_failure(agent.name)

        return responses

    async def _execute_and_validate(
        self,
        query_context: Dict[str, Any],
        input_data: Dict[str, Any],
        reasoning_result,
        request_id: str,
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        """
        Execute agents with validation and retry on failure.

        This method:
        1. Executes selected agents
        2. Validates responses against original query
        3. Detects hallucinations
        4. Calculates confidence score
        5. Retries if validation fails
        6. Logs all interactions and decisions

        Args:
            query_context: Query logging context
            input_data: Original user query/input
            reasoning_result: Result from reasoning engine
            request_id: Request ID
            max_retries: Maximum retry attempts on validation failure

        Returns:
            Formatted output dictionary
        """
        retry_attempt = 0

        while retry_attempt <= max_retries:
            # Execute agents
            agent_responses = await self._execute_agents(
                reasoning_result.agents,
                input_data,
                reasoning_result.parallel,
                reasoning_result.parameters,
            )

            # Log agent interactions
            for response in agent_responses:
                self.query_logger.log_agent_interaction(
                    query_context,
                    agent_name=response.agent_name,
                    input_data=input_data,
                    output_data=response.data if response.success else {},
                    success=response.success,
                    execution_time_ms=response.execution_time * 1000,
                    error=response.error if not response.success else None,
                )

            # Schema validation (existing)
            validated_responses = self._validate_outputs(agent_responses)

            # Format output for response validation
            output = self.output_formatter.format_multiple_responses(
                validated_responses,
                request_id=request_id,
                aggregate=True,
            )

            # Add reasoning information
            output = self.output_formatter.enrich_with_reasoning(output, reasoning_result)

            # Extract agent response data for validation
            agent_response_data = output.get("data", {})

            # Validate response against original query
            validation_result = await self.response_validator.validate_response(
                user_query=input_data,
                agent_responses=agent_response_data,
                reasoning=reasoning_result.__dict__ if reasoning_result else None,
            )

            # Log validation results (including confidence score)
            self.query_logger.log_validation(
                query_context,
                validation_result=validation_result.to_dict(),
                retry_on_failure=(retry_attempt < max_retries and not validation_result.is_valid),
            )

            # Check if validation passed
            if validation_result.is_valid:
                logger.info(
                    f"Response validation passed (confidence: {validation_result.confidence_score:.3f})"
                )
                # Remove confidence score from output (don't send to user)
                # It's only in the logs
                return output

            # Validation failed
            logger.warning(
                f"Response validation failed (attempt {retry_attempt + 1}/{max_retries + 1}): "
                f"confidence={validation_result.confidence_score:.3f}, "
                f"hallucination={validation_result.hallucination_detected}, "
                f"issues={validation_result.issues}"
            )

            # Check if we should retry
            if retry_attempt < max_retries:
                retry_attempt += 1

                # Log retry attempt
                self.query_logger.log_retry_attempt(
                    query_context,
                    attempt_number=retry_attempt,
                    reason=f"Validation failed: {'; '.join(validation_result.issues[:3])}",
                    agents_to_retry=reasoning_result.agents,
                )

                logger.info(f"Retrying with same agents (attempt {retry_attempt + 1}/{max_retries + 1})")

                # Optionally modify parameters for retry (could be enhanced)
                # For now, just retry with same parameters
                continue
            else:
                # Max retries exceeded, return best effort result
                logger.warning(
                    f"Max retries ({max_retries}) exceeded. Returning result with validation warnings."
                )

                # Add validation warning to metadata (but not confidence score)
                if "_metadata" not in output:
                    output["_metadata"] = {}

                output["_metadata"]["validation_warning"] = {
                    "message": "Response validation failed after retries",
                    "issues": validation_result.issues,
                    "hallucination_detected": validation_result.hallucination_detected,
                }

                return output

    def _validate_outputs(self, agent_responses):
        """Validate agent outputs against schemas if configured."""
        if not self.config.validation.schema_name:
            return agent_responses

        validated = []
        for response in agent_responses:
            if not response.success:
                validated.append(response)
                continue

            # Validate against schema
            is_valid, errors = self.schema_validator.validate(
                data=response.data,
                schema_name=self.config.validation.schema_name,
                strict=self.config.validation.strict,
            )

            if not is_valid:
                logger.warning(
                    f"Output validation failed for {response.agent_name}: {errors}"
                )
                if self.config.validation.strict:
                    response.success = False
                    response.error = f"Validation failed: {'; '.join(errors)}"

            validated.append(response)

        return validated

    def _record_execution(self, **kwargs):
        """Record execution in audit log."""
        execution_record = {
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs,
        }
        self._execution_history.append(execution_record)

        # Keep only last 1000 records in memory
        if len(self._execution_history) > 1000:
            self._execution_history = self._execution_history[-1000:]

    async def cleanup(self) -> None:
        """Clean up orchestrator resources."""
        logger.info("Cleaning up orchestrator")
        await self.agent_registry.cleanup_all()
        self._initialized = False

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            "name": self.config.name,
            "initialized": self._initialized,
            "request_count": self._request_count,
            "agents": self.agent_registry.get_stats(),
            "reasoning": self.hybrid_reasoner.get_stats() if self.hybrid_reasoner else {},
            "schemas": self.schema_validator.list_schemas(),
        }
