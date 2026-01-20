"""
Main orchestrator class for agent coordination.

This module provides the core Orchestrator class that ties together all components:
- Agent registry and management
- Reasoning engines (rule-based, AI, hybrid)
- Output validation and formatting
- Retry and fallback logic
- Security validation
- Observability (metrics, tracing, logging)
"""

import asyncio
import logging
import os
import time
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
from .formatting import ResponseFormatter
from .observability import (
    orchestrator_metrics,
    metrics_server,
    init_tracing,
    get_tracer,
    create_span,
    end_span,
    TracingContext,
    orchestrator_cost_tracker,
    sanitize_data,
    setup_orchestrator_logging,
    get_logger as get_structured_logger,
    RequestContext,
    set_correlation_id,
    set_session_id,
    get_correlation_id,
    get_session_id,
)
from .reasoning import AIReasoner, BedrockReasoner, GatewayReasoner, HybridReasoner, RuleEngine
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
structured_logger = None  # Will be initialized in __init__


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

        # Setup observability
        self._setup_observability()

        # Setup logging (traditional)
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

            elif self.config.ai_provider == "gateway":
                # Model Gateway provider
                if not self.config.gateway:
                    raise ConfigurationError(
                        "Gateway configuration required when ai_provider is 'gateway'"
                    )

                self.ai_reasoner = GatewayReasoner(
                    gateway_url=self.config.gateway.url,
                    provider=self.config.gateway.provider,
                    model=self.config.gateway.model,
                    api_key=self.config.gateway.api_key,
                )
                logger.info(
                    f"Initialized Gateway AI reasoner: url={self.config.gateway.url}, "
                    f"provider={self.config.gateway.provider or 'default'}, "
                    f"model={self.config.gateway.model or 'default'}"
                )

            else:
                raise ConfigurationError(
                    f"Invalid ai_provider: {self.config.ai_provider}. Must be 'anthropic', 'bedrock', or 'gateway'"
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

        # Initialize response formatter for user-friendly output
        self.response_formatter = ResponseFormatter()

        # Execution context
        self._execution_history: List[Dict[str, Any]] = []

        logger.info(f"Orchestrator initialized: {self.config.name}")

    def _setup_observability(self):
        """Initialize observability components (metrics, tracing, logging)."""
        global structured_logger
        obs_config = self.config.observability

        # 1. Setup distributed tracing (OpenTelemetry with OTLP)
        if obs_config.enable_tracing:
            try:
                # Allow environment variable to override config
                otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or obs_config.otlp_endpoint

                init_tracing(
                    service_name=self.config.name,
                    service_version="1.0.0",
                    otlp_endpoint=otlp_endpoint,
                    enable_console=obs_config.enable_console_traces,
                )
                logger.info(
                    f"Distributed tracing initialized "
                    f"(OTLP endpoint: {otlp_endpoint or 'None'})"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize tracing: {e}")

        # 2. Setup structured logging
        if obs_config.enable_structured_logging:
            try:
                setup_orchestrator_logging(
                    log_level=self.config.log_level,
                    log_file=obs_config.log_file,
                    enable_console=True,
                    json_format=True,
                    enable_rotation=obs_config.enable_log_rotation,
                    max_bytes=obs_config.log_max_bytes,
                    backup_count=obs_config.log_backup_count,
                    sanitize_logs=obs_config.enable_sanitization,
                )
                structured_logger = get_structured_logger(__name__)
                logger.info("Structured JSON logging initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize structured logging: {e}")

        # 3. Start metrics HTTP server for Prometheus scraping
        if obs_config.enable_metrics:
            try:
                metrics_server.port = obs_config.metrics_port
                metrics_server.start_in_background()
                logger.info(f"Prometheus metrics server starting on port {obs_config.metrics_port}")
            except Exception as e:
                logger.warning(f"Failed to start metrics server: {e}")

        # 4. Cost tracking is always available via orchestrator_cost_tracker singleton
        if obs_config.enable_cost_tracking:
            logger.info("AI reasoner cost tracking enabled")

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

    async def reload_agents(self) -> Dict[str, Any]:
        """
        Reload agent configuration and re-register agents without restarting the orchestrator.

        This allows adding/removing/updating agents dynamically by:
        1. Re-loading configuration from agents.yaml
        2. Cleaning up existing agents
        3. Re-registering agents from updated config

        Returns:
            Dict with reload results including counts and any errors
        """
        logger.info("🔄 Reloading agents from configuration...")

        try:
            # Re-load configuration
            from .config import load_agents_config
            agents_config_path = os.path.join(
                os.path.dirname(self.config_path),
                "config/agents.yaml"
            )

            old_count = self.agent_registry.count()
            old_agents = list(self.agent_registry.list_agents().keys())

            # Clean up existing agents
            await self.agent_registry.cleanup_all()
            logger.info(f"Cleaned up {old_count} existing agents")

            # Reload config
            self.agents_config = load_agents_config(agents_config_path)
            logger.info(f"Reloaded configuration with {len(self.agents_config.agents)} agents")

            # Re-register agents
            registered = []
            skipped = []
            failed = []

            for agent_config in self.agents_config.agents:
                if not agent_config.enabled:
                    skipped.append(agent_config.name)
                    logger.info(f"Skipping disabled agent: {agent_config.name}")
                    continue

                try:
                    agent = self._create_agent(agent_config)
                    await self.agent_registry.register(agent, initialize=True)
                    registered.append(agent_config.name)
                    logger.info(f"Registered agent: {agent_config.name}")
                except Exception as e:
                    failed.append({
                        "name": agent_config.name,
                        "error": str(e)
                    })
                    logger.error(f"Failed to register agent {agent_config.name}: {e}")

            new_count = self.agent_registry.count()
            new_agents = list(self.agent_registry.list_agents().keys())

            # Calculate changes
            added = [a for a in new_agents if a not in old_agents]
            removed = [a for a in old_agents if a not in new_agents]

            result = {
                "success": True,
                "message": f"Agents reloaded successfully",
                "summary": {
                    "previous_count": old_count,
                    "current_count": new_count,
                    "registered": len(registered),
                    "skipped": len(skipped),
                    "failed": len(failed),
                },
                "changes": {
                    "added": added,
                    "removed": removed,
                    "updated": [a for a in new_agents if a in old_agents and a not in added],
                },
                "agents": {
                    "registered": registered,
                    "skipped": skipped,
                    "failed": failed,
                },
            }

            logger.info(
                f"✅ Agent reload complete: {new_count} agents active "
                f"(+{len(added)}, -{len(removed)})"
            )

            # Update metrics
            orchestrator_metrics.registered_agents.set(new_count)

            return result

        except Exception as e:
            logger.error(f"❌ Failed to reload agents: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }

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
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process input through the orchestrator.

        Main entry point for orchestrating agent calls with:
        - Response validation against user query
        - Hallucination detection
        - Confidence scoring (logged, not sent to user)
        - Retry on validation failure
        - Comprehensive per-query logging
        - Full observability (metrics, tracing, cost tracking)

        Args:
            input_data: Input data to process
            validate_input_security: Whether to validate input for security issues
            request_id: Optional request ID for tracking (correlation ID)
            session_id: Optional session ID for multi-request conversations

        Returns:
            Formatted output dictionary with results
        """
        if not self._initialized:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")

        # Generate request ID if not provided (correlation ID)
        request_id = request_id or str(uuid.uuid4())
        start_time = datetime.utcnow()
        start_time_monotonic = time.time()

        # Setup request context (correlation ID and session ID)
        with RequestContext(correlation_id=request_id, session_id=session_id):
            logger.info(
                f"Processing request {request_id} "
                f"(session: {get_session_id() or 'N/A'})"
            )
            self._request_count += 1

            # Update metrics - active queries
            orchestrator_metrics.active_queries.inc()

            try:
                # Create distributed tracing span for entire query
                return await self._process_with_observability(
                    input_data=input_data,
                    validate_input_security=validate_input_security,
                    request_id=request_id,
                    start_time=start_time,
                    start_time_monotonic=start_time_monotonic,
                )
            finally:
                # Always decrement active queries
                orchestrator_metrics.active_queries.dec()

    async def _process_with_observability(
        self,
        input_data: Dict[str, Any],
        validate_input_security: bool,
        request_id: str,
        start_time: datetime,
        start_time_monotonic: float,
    ) -> Dict[str, Any]:
        """Process request with full observability integration."""
        # Create query logging context
        query_context = self.query_logger.create_query_context(input_data)

        # Create distributed tracing span for query
        with TracingContext("orchestrator.process_query") as span:
            span.set_attribute("request_id", request_id)
            span.set_attribute("reasoning_mode", self.config.reasoning_mode)

            try:
                # Step 1: Security validation
                if validate_input_security:
                    with TracingContext("orchestrator.security_validation"):
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

                            # Record metrics
                            orchestrator_metrics.queries_failed.labels(
                                error_type="SecurityError",
                                reasoning_mode=self.config.reasoning_mode
                            ).inc()

                            output = self.output_formatter.create_error_output(
                                error_message=error_msg,
                                request_id=request_id,
                            )
                            self.query_logger.finalize_query_log(query_context, output)
                            return output

                # Step 2: Reasoning - determine which agents to call
                reasoning_result = await self._reason_with_observability(input_data, span)
                if not reasoning_result:
                    error_msg = "No agents could be determined for this request"
                    self.query_logger.log_error(
                        query_context,
                        error_type="ReasoningError",
                        error_message=error_msg,
                    )

                    # Record metrics
                    orchestrator_metrics.queries_failed.labels(
                        error_type="ReasoningError",
                        reasoning_mode=self.config.reasoning_mode
                    ).inc()

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
                    parent_span=span,
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

                # Record success metrics
                duration_seconds = time.time() - start_time_monotonic
                orchestrator_metrics.queries_total.labels(
                    status="success",
                    reasoning_mode=self.config.reasoning_mode
                ).inc()
                orchestrator_metrics.queries_success.labels(
                    reasoning_mode=self.config.reasoning_mode
                ).inc()
                orchestrator_metrics.query_duration.labels(
                    reasoning_mode=self.config.reasoning_mode
                ).observe(duration_seconds)

                # Update session metrics
                orchestrator_metrics.queries_per_session.observe(1)

                logger.info(f"Request {request_id} completed successfully in {duration_seconds:.3f}s")
                return output

            except Exception as e:
                logger.error(f"Error processing request {request_id}: {e}", exc_info=True)
                self.query_logger.log_error(
                    query_context,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    error_details={"traceback": str(e)},
                )

                # Record failure metrics
                duration_seconds = time.time() - start_time_monotonic
                orchestrator_metrics.queries_total.labels(
                    status="failed",
                    reasoning_mode=self.config.reasoning_mode
                ).inc()
                orchestrator_metrics.queries_failed.labels(
                    error_type=type(e).__name__,
                    reasoning_mode=self.config.reasoning_mode
                ).inc()
                orchestrator_metrics.query_duration.labels(
                    reasoning_mode=self.config.reasoning_mode
                ).observe(duration_seconds)

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

    async def _reason_with_observability(self, input_data: Dict[str, Any], parent_span):
        """Reasoning with full observability (metrics, tracing, cost tracking)."""
        start_time = time.time()

        # Create span for reasoning
        with TracingContext("orchestrator.reasoning") as reasoning_span:
            reasoning_span.set_attribute("reasoning_mode", self.config.reasoning_mode)

            # Execute reasoning
            reasoning_result = await self._reason(input_data)

            if not reasoning_result:
                return None

            # Record reasoning metrics
            duration_seconds = time.time() - start_time
            orchestrator_metrics.reasoning_decisions.labels(
                reasoning_mode=self.config.reasoning_mode,
                method=reasoning_result.method
            ).inc()
            orchestrator_metrics.reasoning_confidence.labels(
                method=reasoning_result.method
            ).observe(reasoning_result.confidence)
            orchestrator_metrics.reasoning_duration.labels(
                method=reasoning_result.method
            ).observe(duration_seconds)

            # Add attributes to span
            reasoning_span.set_attribute("agents_selected", len(reasoning_result.agents))
            reasoning_span.set_attribute("confidence", reasoning_result.confidence)
            reasoning_span.set_attribute("method", reasoning_result.method)
            reasoning_span.set_attribute("parallel", reasoning_result.parallel)

            # Track AI reasoner cost if AI was used
            if self.config.observability.enable_cost_tracking and reasoning_result.method in ["ai", "hybrid"]:
                # Check if AI reasoner has usage data
                if hasattr(self.ai_reasoner, "last_usage") and self.ai_reasoner.last_usage:
                    usage = self.ai_reasoner.last_usage
                    cost_data = orchestrator_cost_tracker.track_reasoning_cost(
                        model=usage.get("model", self.config.ai_model),
                        input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0),
                        provider=self.config.ai_provider,
                    )

                    # Record cost metrics
                    orchestrator_metrics.ai_reasoner_cost.labels(
                        provider=self.config.ai_provider,
                        model=usage.get("model", self.config.ai_model)
                    ).inc(cost_data["cost_usd"])
                    orchestrator_metrics.ai_reasoner_tokens.labels(
                        provider=self.config.ai_provider,
                        model=usage.get("model", self.config.ai_model),
                        token_type="input"
                    ).inc(cost_data["input_tokens"])
                    orchestrator_metrics.ai_reasoner_tokens.labels(
                        provider=self.config.ai_provider,
                        model=usage.get("model", self.config.ai_model),
                        token_type="output"
                    ).inc(cost_data["output_tokens"])

            return reasoning_result

    async def _execute_agents(
        self,
        agent_names: List[str],
        input_data: Dict[str, Any],
        parallel: bool,
        parameters: Dict[str, Dict[str, Any]],
    ):
        """
        Execute the selected agents with retry and fallback logic.

        Supports:
        - Multiple calls to the same agent with numbered parameters (weather_1, weather_2)
        - Data chaining: extracting data from previous responses
        """
        agents = []
        agent_instances = []  # Track (agent, param_key, params) for each call
        fallback_map = {}

        # Count occurrences of each agent name for numbering
        agent_counts = {}
        for agent_name in agent_names:
            agent_counts[agent_name] = agent_counts.get(agent_name, 0) + 1

        # Build agent instances with proper parameter mapping
        agent_call_index = {}  # Track which call number we're on for each agent
        for agent_name in agent_names:
            agent = self.agent_registry.get(agent_name)
            if not agent:
                logger.warning(f"Agent {agent_name} not found in registry")
                continue

            # Determine parameter key for this instance
            if agent_counts[agent_name] > 1:
                # Multiple calls - use numbered suffix
                call_num = agent_call_index.get(agent_name, 0) + 1
                agent_call_index[agent_name] = call_num
                param_key = f"{agent_name}_{call_num}"
            else:
                # Single call - use agent name
                param_key = agent_name

            # Get parameters for this specific call
            agent_params = parameters.get(param_key, {})

            agent_instances.append({
                "agent": agent,
                "param_key": param_key,
                "params": agent_params,
            })
            agents.append(agent)

            # Get fallback agent from configuration
            agent_config = self.agents_config.get_agent(agent_name)
            if agent_config and agent_config.fallback:
                fallback_map[agent_name] = agent_config.fallback

        if not agents:
            logger.error("No valid agents found for execution")
            return []

        logger.info(f"Executing {len(agents)} agent calls (parallel={parallel})")
        for idx, inst in enumerate(agent_instances):
            logger.info(f"  Call {idx + 1}: {inst['agent'].name} (params: {inst['param_key']})")

        # Execute with retry handler
        if parallel:
            # Call agents in parallel with agent-specific parameters
            per_agent_input = {}
            for idx, inst in enumerate(agent_instances):
                agent_input = {**input_data, **inst["params"]}
                # Use unique key for each instance
                unique_key = f"{inst['agent'].name}_{idx}"
                per_agent_input[unique_key] = agent_input

            responses = await self.retry_handler.call_multiple_with_retry(
                agents=agents,
                input_data=input_data,
                timeout=self.config.default_timeout,
                fallback_map=fallback_map,
                parallel=True,
                per_agent_input=per_agent_input,
            )
        else:
            # Call agents sequentially with data chaining support
            responses = []
            previous_responses = []  # Track responses for data extraction

            for idx, inst in enumerate(agent_instances):
                agent = inst["agent"]
                agent_params = inst["params"].copy()

                # Check if this agent needs data from previous responses
                if agent_params.get("data_source") == "previous":
                    logger.info(f"Agent {agent.name} requires data from previous responses")
                    # Extract data from previous responses
                    extracted_data = self._extract_data_from_responses(
                        previous_responses,
                        field=agent_params.get("field"),
                        operation=agent_params.get("operation")
                    )
                    # Merge extracted data into parameters
                    agent_params.update(extracted_data)
                    # Remove meta parameters
                    agent_params.pop("data_source", None)
                    agent_params.pop("field", None)

                agent_input = {**input_data, **agent_params}
                response = await self.retry_handler.call_with_retry(
                    agent=agent,
                    input_data=agent_input,
                    timeout=self.config.default_timeout,
                    fallback_agent_name=fallback_map.get(agent.name),
                )
                responses.append(response)
                previous_responses.append(response)

                # Update circuit breaker
                if response.success:
                    self.circuit_breaker.record_success(agent.name)
                else:
                    self.circuit_breaker.record_failure(agent.name)

        return responses

    def _extract_data_from_responses(
        self,
        responses: List[Any],
        field: Optional[str] = None,
        operation: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract data from previous agent responses for chaining.

        Args:
            responses: List of previous agent responses
            field: Field to extract from responses (e.g., "temp", "temperature")
            operation: Operation to perform (e.g., "average", "sum")

        Returns:
            Dictionary with extracted/computed data as parameters
        """
        if not responses:
            logger.warning("No previous responses to extract data from")
            return {}

        extracted_values = []

        # Extract specified field from each response
        for response in responses:
            if not response.success:
                logger.warning(f"Skipping failed response from {response.agent_name}")
                continue

            value = None
            if field and response.data:
                # Try to extract the field from response data
                if isinstance(response.data, dict):
                    # Handle nested structures (e.g., current.temp in weather)
                    if "current" in response.data and field in ["temp", "temperature"]:
                        value = response.data["current"].get("temp")
                    else:
                        value = response.data.get(field)

            if value is not None:
                extracted_values.append(value)
                logger.info(f"Extracted {field}={value} from {response.agent_name}")

        if not extracted_values:
            logger.warning(f"No values extracted for field '{field}'")
            return {}

        # Return extracted values formatted for calculator
        if operation:
            return {
                "operation": operation,
                "operands": extracted_values,
            }
        else:
            return {"values": extracted_values}

    async def _execute_and_validate(
        self,
        query_context: Dict[str, Any],
        input_data: Dict[str, Any],
        reasoning_result,
        request_id: str,
        max_retries: int = 2,
        parent_span=None,
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
            # Execute agents with tracing
            with TracingContext("orchestrator.execute_agents") as exec_span:
                exec_span.set_attribute("agents", str(reasoning_result.agents))
                exec_span.set_attribute("parallel", reasoning_result.parallel)
                exec_span.set_attribute("retry_attempt", retry_attempt)

                # Execute agents
                agent_responses = await self._execute_agents(
                    reasoning_result.agents,
                    input_data,
                    reasoning_result.parallel,
                    reasoning_result.parameters,
                )

                # Log agent interactions and record metrics
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

                    # Record agent metrics
                    status = "success" if response.success else "failed"
                    orchestrator_metrics.agent_calls_total.labels(
                        agent_name=response.agent_name,
                        status=status
                    ).inc()
                    orchestrator_metrics.agent_duration.labels(
                        agent_name=response.agent_name
                    ).observe(response.execution_time)

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
            with TracingContext("orchestrator.validate_response") as val_span:
                validation_result = await self.response_validator.validate_response(
                    user_query=input_data,
                    agent_responses=agent_response_data,
                    reasoning=reasoning_result.__dict__ if reasoning_result else None,
                )

                val_span.set_attribute("is_valid", validation_result.is_valid)
                val_span.set_attribute("confidence", validation_result.confidence_score)
                val_span.set_attribute("hallucination_detected", validation_result.hallucination_detected)

            # Log validation results (including confidence score)
            self.query_logger.log_validation(
                query_context,
                validation_result=validation_result.to_dict(),
                retry_on_failure=(retry_attempt < max_retries and not validation_result.is_valid),
            )

            # Record validation metrics
            result = "valid" if validation_result.is_valid else "invalid"
            orchestrator_metrics.validation_checks.labels(result=result).inc()
            orchestrator_metrics.validation_confidence.observe(validation_result.confidence_score)
            if validation_result.hallucination_detected:
                orchestrator_metrics.hallucination_detected.inc()

            # Check if validation passed
            if validation_result.is_valid:
                logger.info(
                    f"Response validation passed (confidence: {validation_result.confidence_score:.3f})"
                )
                # Remove confidence score from output (don't send to user)
                # It's only in the logs

                # Add formatted text for user-friendly display
                agent_data = output.get("data", {})
                formatted_text = self.response_formatter.format_response(agent_data)
                output["formatted_text"] = formatted_text

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

                # Record retry metrics
                for agent_name in reasoning_result.agents:
                    orchestrator_metrics.agent_retries.labels(
                        agent_name=agent_name,
                        reason="validation_failed"
                    ).inc()

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

                # Add formatted text for user-friendly display
                agent_data = output.get("data", {})
                formatted_text = self.response_formatter.format_response(agent_data)
                output["formatted_text"] = formatted_text

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
        """Get orchestrator statistics including observability metrics."""
        stats = {
            "name": self.config.name,
            "initialized": self._initialized,
            "request_count": self._request_count,
            "agents": self.agent_registry.get_stats(),
            "reasoning": self.hybrid_reasoner.get_stats() if self.hybrid_reasoner else {},
            "schemas": self.schema_validator.list_schemas(),
        }

        # Add observability stats if enabled
        if self.config.observability.enable_cost_tracking:
            stats["cost_tracking"] = orchestrator_cost_tracker.get_statistics()

        # Add circuit breaker stats
        circuit_breaker_stats = {}
        for agent in self.agent_registry.get_all():
            if self.circuit_breaker.is_open(agent.name):
                circuit_breaker_stats[agent.name] = "open"
                # Update circuit breaker metric
                orchestrator_metrics.circuit_breaker_open.labels(agent_name=agent.name).set(1)
            else:
                orchestrator_metrics.circuit_breaker_open.labels(agent_name=agent.name).set(0)

        if circuit_breaker_stats:
            stats["circuit_breakers"] = circuit_breaker_stats

        # Update system metrics
        orchestrator_metrics.registered_agents.set(self.agent_registry.count())

        return stats
