"""
Per-query logging system.

Logs all interactions, decisions, and validations for each user query.
Creates detailed audit trail for debugging and monitoring.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid


class QueryLogger:
    """
    Logs detailed information for each query.

    Creates structured logs containing:
    - User query
    - Reasoning decisions (rule/AI/hybrid)
    - Agent selection and execution
    - Tool interactions
    - Validation results
    - Confidence scores
    - Retry attempts
    - Errors
    - Timing information
    """

    def __init__(
        self,
        log_dir: str = "logs/queries",
        log_to_file: bool = True,
        log_to_console: bool = True,
    ):
        """
        Initialize query logger.

        Args:
            log_dir: Directory to store query logs
            log_to_file: Whether to log to files
            log_to_console: Whether to log to console
        """
        self.log_dir = Path(log_dir)
        self.log_to_file = log_to_file
        self.log_to_console = log_to_console

        # Create log directory
        if self.log_to_file:
            self.log_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(__name__)

    def create_query_context(self, user_query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new query context for logging.

        Args:
            user_query: The user's query

        Returns:
            Query context dictionary
        """
        query_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        context = {
            "query_id": query_id,
            "timestamp": timestamp,
            "user_query": user_query,
            "reasoning": {},
            "agent_interactions": [],
            "tool_interactions": [],
            "validation": {},
            "retry_attempts": [],
            "errors": [],
            "timing": {
                "start_time": timestamp,
                "end_time": None,
                "total_duration_ms": None,
            },
            "final_result": {},
        }

        self._log_event(query_id, "QUERY_START", {"query": user_query})

        return context

    def log_reasoning(
        self,
        query_context: Dict[str, Any],
        reasoning_mode: str,
        reasoning_result: Dict[str, Any],
    ):
        """
        Log reasoning decision.

        Args:
            query_context: Query context
            reasoning_mode: Mode used (rule/AI/hybrid)
            reasoning_result: Reasoning result details
        """
        query_id = query_context["query_id"]

        reasoning_log = {
            "mode": reasoning_mode,
            "timestamp": datetime.utcnow().isoformat(),
            "selected_agents": reasoning_result.get("agents", []),
            "confidence": reasoning_result.get("confidence", None),
            "method": reasoning_result.get("method", None),
            "reasoning_text": reasoning_result.get("reasoning", ""),
            "parallel": reasoning_result.get("parallel", False),
            "parameters": reasoning_result.get("parameters", {}),
        }

        query_context["reasoning"] = reasoning_log

        self._log_event(
            query_id,
            "REASONING_DECISION",
            {
                "mode": reasoning_mode,
                "selected_agents": reasoning_log["selected_agents"],
                "method": reasoning_log["method"],
                "confidence": reasoning_log["confidence"],
            },
        )

    def log_agent_interaction(
        self,
        query_context: Dict[str, Any],
        agent_name: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        success: bool,
        execution_time_ms: float,
        error: Optional[str] = None,
    ):
        """
        Log agent interaction.

        Args:
            query_context: Query context
            agent_name: Name of the agent
            input_data: Input sent to agent
            output_data: Output received from agent
            success: Whether interaction succeeded
            execution_time_ms: Execution time in milliseconds
            error: Error message if failed
        """
        query_id = query_context["query_id"]

        interaction_log = {
            "agent_name": agent_name,
            "timestamp": datetime.utcnow().isoformat(),
            "input": input_data,
            "output": output_data,
            "success": success,
            "execution_time_ms": execution_time_ms,
            "error": error,
        }

        query_context["agent_interactions"].append(interaction_log)

        self._log_event(
            query_id,
            "AGENT_INTERACTION",
            {
                "agent": agent_name,
                "success": success,
                "execution_time_ms": execution_time_ms,
                "error": error,
            },
        )

    def log_tool_interaction(
        self,
        query_context: Dict[str, Any],
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: Any,
        success: bool,
        execution_time_ms: float,
    ):
        """
        Log tool interaction.

        Args:
            query_context: Query context
            tool_name: Name of the tool
            tool_input: Input to tool
            tool_output: Output from tool
            success: Whether tool call succeeded
            execution_time_ms: Execution time in milliseconds
        """
        query_id = query_context["query_id"]

        tool_log = {
            "tool_name": tool_name,
            "timestamp": datetime.utcnow().isoformat(),
            "input": tool_input,
            "output": tool_output,
            "success": success,
            "execution_time_ms": execution_time_ms,
        }

        query_context["tool_interactions"].append(tool_log)

        self._log_event(
            query_id,
            "TOOL_INTERACTION",
            {
                "tool": tool_name,
                "success": success,
                "execution_time_ms": execution_time_ms,
            },
        )

    def log_validation(
        self,
        query_context: Dict[str, Any],
        validation_result: Dict[str, Any],
        retry_on_failure: bool = False,
    ):
        """
        Log validation results.

        Args:
            query_context: Query context
            validation_result: Validation result details
            retry_on_failure: Whether retry will be attempted
        """
        query_id = query_context["query_id"]

        validation_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "is_valid": validation_result.get("is_valid", False),
            "confidence_score": validation_result.get("confidence_score", 0.0),
            "hallucination_detected": validation_result.get(
                "hallucination_detected", False
            ),
            "validation_details": validation_result.get("validation_details", {}),
            "issues": validation_result.get("issues", []),
            "retry_on_failure": retry_on_failure,
        }

        query_context["validation"] = validation_log

        self._log_event(
            query_id,
            "VALIDATION",
            {
                "is_valid": validation_log["is_valid"],
                "confidence_score": validation_log["confidence_score"],
                "hallucination_detected": validation_log["hallucination_detected"],
                "issues_count": len(validation_log["issues"]),
                "retry_on_failure": retry_on_failure,
            },
        )

    def log_retry_attempt(
        self,
        query_context: Dict[str, Any],
        attempt_number: int,
        reason: str,
        agents_to_retry: List[str],
    ):
        """
        Log retry attempt.

        Args:
            query_context: Query context
            attempt_number: Retry attempt number
            reason: Reason for retry
            agents_to_retry: List of agents being retried
        """
        query_id = query_context["query_id"]

        retry_log = {
            "attempt_number": attempt_number,
            "timestamp": datetime.utcnow().isoformat(),
            "reason": reason,
            "agents_to_retry": agents_to_retry,
        }

        query_context["retry_attempts"].append(retry_log)

        self._log_event(
            query_id,
            "RETRY_ATTEMPT",
            {
                "attempt": attempt_number,
                "reason": reason,
                "agents": agents_to_retry,
            },
        )

    def log_error(
        self,
        query_context: Dict[str, Any],
        error_type: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
    ):
        """
        Log error.

        Args:
            query_context: Query context
            error_type: Type of error
            error_message: Error message
            error_details: Additional error details
        """
        query_id = query_context["query_id"]

        error_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "error_details": error_details or {},
        }

        query_context["errors"].append(error_log)

        self._log_event(
            query_id,
            "ERROR",
            {
                "error_type": error_type,
                "error_message": error_message,
            },
        )

    def finalize_query_log(
        self, query_context: Dict[str, Any], final_result: Dict[str, Any]
    ):
        """
        Finalize query log and write to file.

        Args:
            query_context: Query context
            final_result: Final result returned to user
        """
        query_id = query_context["query_id"]

        # Update timing
        end_time = datetime.utcnow().isoformat()
        start_time = datetime.fromisoformat(query_context["timing"]["start_time"])
        end_time_dt = datetime.fromisoformat(end_time)
        duration_ms = (end_time_dt - start_time).total_seconds() * 1000

        query_context["timing"]["end_time"] = end_time
        query_context["timing"]["total_duration_ms"] = duration_ms

        # Store final result (excluding sensitive data, keeping confidence internal)
        query_context["final_result"] = {
            "success": final_result.get("success", False),
            "agent_count": len(final_result.get("data", {})),
            "agents_used": list(final_result.get("data", {}).keys()),
            "error_count": len(final_result.get("errors", [])),
        }

        # Write to file
        if self.log_to_file:
            self._write_query_log_file(query_context)

        # Log summary to console
        if self.log_to_console:
            self._log_query_summary(query_context)

        self._log_event(
            query_id,
            "QUERY_END",
            {
                "success": query_context["final_result"]["success"],
                "duration_ms": duration_ms,
                "agents_used": query_context["final_result"]["agents_used"],
            },
        )

    def _write_query_log_file(self, query_context: Dict[str, Any]):
        """Write query log to JSON file."""
        query_id = query_context["query_id"]
        timestamp = query_context["timestamp"].replace(":", "-").replace(".", "-")

        # Create filename with timestamp and query ID
        filename = f"query_{timestamp}_{query_id[:8]}.json"
        filepath = self.log_dir / filename

        try:
            with open(filepath, "w") as f:
                json.dump(query_context, f, indent=2, default=str)

            self.logger.info(f"Query log written to {filepath}")

        except Exception as e:
            self.logger.error(f"Failed to write query log: {e}")

    def _log_query_summary(self, query_context: Dict[str, Any]):
        """Log query summary to console."""
        query_id = query_context["query_id"]
        success = query_context["final_result"]["success"]
        duration = query_context["timing"]["total_duration_ms"]
        agents = query_context["final_result"]["agents_used"]

        validation = query_context.get("validation", {})
        confidence = validation.get("confidence_score", 0.0)
        hallucination = validation.get("hallucination_detected", False)

        retry_count = len(query_context.get("retry_attempts", []))
        error_count = len(query_context.get("errors", []))

        summary = (
            f"\n{'='*70}\n"
            f"Query Summary [{query_id[:8]}]\n"
            f"{'='*70}\n"
            f"Status: {'✅ SUCCESS' if success else '❌ FAILED'}\n"
            f"Duration: {duration:.2f}ms\n"
            f"Agents: {', '.join(agents) if agents else 'None'}\n"
            f"Confidence: {confidence:.3f}\n"
            f"Hallucination: {'⚠️  YES' if hallucination else '✅ NO'}\n"
            f"Retries: {retry_count}\n"
            f"Errors: {error_count}\n"
            f"{'='*70}\n"
        )

        self.logger.info(summary)

    def _log_event(self, query_id: str, event_type: str, event_data: Dict[str, Any]):
        """Log individual event."""
        event = {
            "query_id": query_id[:8],
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": event_data,
        }

        self.logger.debug(f"[{event['query_id']}] {event_type}: {json.dumps(event_data)}")


class QueryLogReader:
    """Utility for reading and analyzing query logs."""

    def __init__(self, log_dir: str = "logs/queries"):
        """
        Initialize query log reader.

        Args:
            log_dir: Directory containing query logs
        """
        self.log_dir = Path(log_dir)

    def get_recent_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most recent query logs.

        Args:
            limit: Maximum number of logs to return

        Returns:
            List of query contexts
        """
        if not self.log_dir.exists():
            return []

        # Get all log files
        log_files = sorted(
            self.log_dir.glob("query_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        # Read recent logs
        logs = []
        for log_file in log_files[:limit]:
            try:
                with open(log_file, "r") as f:
                    logs.append(json.load(f))
            except Exception as e:
                logging.error(f"Failed to read log {log_file}: {e}")

        return logs

    def get_query_by_id(self, query_id: str) -> Optional[Dict[str, Any]]:
        """
        Get query log by ID.

        Args:
            query_id: Query ID (full or prefix)

        Returns:
            Query context or None
        """
        if not self.log_dir.exists():
            return None

        # Search for matching file
        for log_file in self.log_dir.glob(f"query_*{query_id[:8]}*.json"):
            try:
                with open(log_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Failed to read log {log_file}: {e}")

        return None

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics from query logs.

        Returns:
            Statistics dictionary
        """
        logs = self.get_recent_queries(limit=1000)

        if not logs:
            return {
                "total_queries": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0.0,
                "avg_confidence": 0.0,
                "hallucination_rate": 0.0,
                "retry_rate": 0.0,
            }

        total = len(logs)
        successful = sum(1 for log in logs if log["final_result"]["success"])
        durations = [
            log["timing"]["total_duration_ms"]
            for log in logs
            if log["timing"]["total_duration_ms"]
        ]
        confidences = [
            log["validation"]["confidence_score"]
            for log in logs
            if log.get("validation", {}).get("confidence_score") is not None
        ]
        hallucinations = sum(
            1
            for log in logs
            if log.get("validation", {}).get("hallucination_detected", False)
        )
        retries = sum(1 for log in logs if log.get("retry_attempts"))

        return {
            "total_queries": total,
            "success_rate": successful / total if total > 0 else 0.0,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0.0,
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
            "hallucination_rate": hallucinations / total if total > 0 else 0.0,
            "retry_rate": retries / total if total > 0 else 0.0,
        }
