"""
Output formatting for agent responses.

This module provides formatting and enrichment of agent outputs,
including metadata addition, JSON formatting, and result aggregation.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..agents.base_agent import AgentResponse

logger = logging.getLogger(__name__)


class OutputFormatter:
    """
    Formatter for agent outputs.

    Enriches outputs with metadata, formats results consistently,
    and aggregates multi-agent responses.
    """

    def __init__(
        self,
        include_metadata: bool = True,
        include_timing: bool = True,
        include_agent_trail: bool = True,
        pretty_print: bool = True,
    ):
        """
        Initialize output formatter.

        Args:
            include_metadata: Include metadata in outputs
            include_timing: Include timing information
            include_agent_trail: Include agent execution trail
            pretty_print: Pretty-print JSON outputs
        """
        self.include_metadata = include_metadata
        self.include_timing = include_timing
        self.include_agent_trail = include_agent_trail
        self.pretty_print = pretty_print

        logger.debug("Output formatter initialized")

    def format_single_response(
        self,
        response: AgentResponse,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Format a single agent response.

        Args:
            response: Agent response to format
            request_id: Optional request ID for tracking

        Returns:
            Formatted output dictionary
        """
        output = {
            "success": response.success,
            "data": response.data,
        }

        if not response.success:
            output["error"] = response.error

        # Add metadata if enabled
        if self.include_metadata:
            metadata = {
                "agent": response.agent_name,
                "timestamp": response.timestamp.isoformat(),
            }

            if self.include_timing:
                metadata["execution_time"] = response.execution_time

            if request_id:
                metadata["request_id"] = request_id

            # Merge with agent-provided metadata
            metadata.update(response.metadata)

            output["_metadata"] = metadata

        return output

    def format_multiple_responses(
        self,
        responses: List[AgentResponse],
        request_id: Optional[str] = None,
        aggregate: bool = True,
    ) -> Dict[str, Any]:
        """
        Format multiple agent responses.

        Args:
            responses: List of agent responses
            request_id: Optional request ID for tracking
            aggregate: Whether to aggregate results or keep separate

        Returns:
            Formatted output dictionary
        """
        if not responses:
            return {
                "success": False,
                "error": "No agent responses",
                "_metadata": {"count": 0}
            }

        if aggregate:
            return self._aggregate_responses(responses, request_id)
        else:
            return self._separate_responses(responses, request_id)

    def _aggregate_responses(
        self,
        responses: List[AgentResponse],
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Aggregate multiple responses into a single output.

        Args:
            responses: List of agent responses
            request_id: Optional request ID

        Returns:
            Aggregated output
        """
        # Determine overall success (all must succeed)
        overall_success = all(r.success for r in responses)

        # Merge data from all successful responses
        merged_data = {}
        errors = []

        for response in responses:
            if response.success:
                merged_data[response.agent_name] = response.data
            else:
                errors.append({
                    "agent": response.agent_name,
                    "error": response.error
                })

        output = {
            "success": overall_success,
            "data": merged_data,
        }

        if errors:
            output["errors"] = errors

        # Add metadata
        if self.include_metadata:
            metadata = {
                "count": len(responses),
                "successful": sum(1 for r in responses if r.success),
                "failed": sum(1 for r in responses if not r.success),
            }

            if self.include_agent_trail:
                metadata["agent_trail"] = [r.agent_name for r in responses]

            if self.include_timing:
                metadata["total_execution_time"] = sum(r.execution_time for r in responses)
                metadata["max_execution_time"] = max(r.execution_time for r in responses)

            if request_id:
                metadata["request_id"] = request_id

            metadata["timestamp"] = datetime.utcnow().isoformat()

            output["_metadata"] = metadata

        return output

    def _separate_responses(
        self,
        responses: List[AgentResponse],
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Keep responses separate in output.

        Args:
            responses: List of agent responses
            request_id: Optional request ID

        Returns:
            Output with separate responses
        """
        formatted_responses = [
            self.format_single_response(r, request_id)
            for r in responses
        ]

        overall_success = all(r.success for r in responses)

        output = {
            "success": overall_success,
            "responses": formatted_responses,
        }

        # Add summary metadata
        if self.include_metadata:
            metadata = {
                "count": len(responses),
                "successful": sum(1 for r in responses if r.success),
                "failed": sum(1 for r in responses if not r.success),
            }

            if self.include_agent_trail:
                metadata["agent_trail"] = [r.agent_name for r in responses]

            if self.include_timing:
                metadata["total_execution_time"] = sum(r.execution_time for r in responses)

            if request_id:
                metadata["request_id"] = request_id

            metadata["timestamp"] = datetime.utcnow().isoformat()

            output["_metadata"] = metadata

        return output

    def to_json(self, output: Dict[str, Any]) -> str:
        """
        Convert output to JSON string.

        Args:
            output: Output dictionary

        Returns:
            JSON string
        """
        if self.pretty_print:
            return json.dumps(output, indent=2, default=str)
        else:
            return json.dumps(output, default=str)

    def enrich_with_reasoning(
        self,
        output: Dict[str, Any],
        reasoning_result: Any,  # ReasoningResult type
    ) -> Dict[str, Any]:
        """
        Enrich output with reasoning information.

        Args:
            output: Output dictionary
            reasoning_result: Reasoning result to add

        Returns:
            Enriched output
        """
        if not self.include_metadata:
            return output

        if "_metadata" not in output:
            output["_metadata"] = {}

        output["_metadata"]["reasoning"] = {
            "method": reasoning_result.method,
            "confidence": reasoning_result.confidence,
            "explanation": reasoning_result.reasoning,
            "parallel": reasoning_result.parallel,
            "selected_agents": reasoning_result.agents if hasattr(reasoning_result, 'agents') else [],
        }

        return output

    def create_error_output(
        self,
        error_message: str,
        request_id: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a standardized error output.

        Args:
            error_message: Error message
            request_id: Optional request ID
            additional_info: Additional error information

        Returns:
            Error output dictionary
        """
        output = {
            "success": False,
            "error": error_message,
            "data": {}
        }

        if self.include_metadata:
            metadata = {
                "timestamp": datetime.utcnow().isoformat(),
            }

            if request_id:
                metadata["request_id"] = request_id

            if additional_info:
                metadata.update(additional_info)

            output["_metadata"] = metadata

        return output
