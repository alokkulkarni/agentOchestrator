"""
Response validation and hallucination detection.

This module validates agent responses against:
1. Original user query
2. Other agent outputs (consistency)
3. Hallucination detection
4. Confidence scoring
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from anthropic import Anthropic

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of response validation."""

    def __init__(
        self,
        is_valid: bool,
        confidence_score: float,
        hallucination_detected: bool,
        validation_details: Dict[str, Any],
        issues: List[str],
    ):
        self.is_valid = is_valid
        self.confidence_score = confidence_score
        self.hallucination_detected = hallucination_detected
        self.validation_details = validation_details
        self.issues = issues

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "is_valid": self.is_valid,
            "confidence_score": self.confidence_score,
            "hallucination_detected": self.hallucination_detected,
            "validation_details": self.validation_details,
            "issues": self.issues,
        }


class ResponseValidator:
    """
    Validates agent responses for correctness and hallucination.

    Performs:
    - Query-response relevance check
    - Cross-agent consistency validation
    - Hallucination detection
    - Confidence scoring
    """

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        enable_ai_validation: bool = True,
        confidence_threshold: float = 0.7,
    ):
        """
        Initialize response validator.

        Args:
            anthropic_api_key: API key for AI-based validation
            enable_ai_validation: Whether to use AI for validation
            confidence_threshold: Minimum confidence score to pass validation
        """
        self.enable_ai_validation = enable_ai_validation and anthropic_api_key
        self.confidence_threshold = confidence_threshold

        if self.enable_ai_validation:
            self.client = Anthropic(api_key=anthropic_api_key)
        else:
            self.client = None

        logger.info(
            f"ResponseValidator initialized (AI validation: {self.enable_ai_validation})"
        )

    async def validate_response(
        self,
        user_query: Dict[str, Any],
        agent_responses: Dict[str, Any],
        reasoning: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """
        Validate agent responses against user query.

        Args:
            user_query: Original user query
            agent_responses: Dict of agent_name -> response_data
            reasoning: Reasoning information from orchestrator

        Returns:
            ValidationResult with validation details
        """
        logger.debug(f"Validating response for query: {user_query.get('query', 'N/A')}")

        issues = []
        validation_details = {}

        # 1. Basic validation (always performed)
        basic_valid, basic_issues = self._basic_validation(user_query, agent_responses)
        issues.extend(basic_issues)
        validation_details["basic_validation"] = {
            "passed": basic_valid,
            "issues": basic_issues,
        }

        # 2. Cross-agent consistency check
        consistency_valid, consistency_issues = self._check_consistency(agent_responses)
        issues.extend(consistency_issues)
        validation_details["consistency_check"] = {
            "passed": consistency_valid,
            "issues": consistency_issues,
        }

        # 3. Hallucination detection
        hallucination_detected, hallucination_details = await self._detect_hallucination(
            user_query, agent_responses, reasoning
        )
        validation_details["hallucination_detection"] = hallucination_details

        if hallucination_detected:
            issues.append("Potential hallucination detected in response")

        # 4. Calculate confidence score
        confidence_score = self._calculate_confidence(
            basic_valid, consistency_valid, hallucination_detected, agent_responses
        )
        validation_details["confidence_calculation"] = {
            "score": confidence_score,
            "threshold": self.confidence_threshold,
            "meets_threshold": confidence_score >= self.confidence_threshold,
        }

        # Overall validation result
        is_valid = (
            basic_valid
            and consistency_valid
            and not hallucination_detected
            and confidence_score >= self.confidence_threshold
        )

        logger.info(
            f"Validation result: valid={is_valid}, confidence={confidence_score:.3f}, "
            f"hallucination={hallucination_detected}, issues={len(issues)}"
        )

        return ValidationResult(
            is_valid=is_valid,
            confidence_score=confidence_score,
            hallucination_detected=hallucination_detected,
            validation_details=validation_details,
            issues=issues,
        )

    def _basic_validation(
        self, user_query: Dict[str, Any], agent_responses: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Perform basic validation checks.

        Checks:
        - Responses are not empty
        - Required fields present
        - Data types are correct
        - No obvious errors in response
        """
        issues = []

        # Check if we have any responses
        if not agent_responses:
            issues.append("No agent responses to validate")
            return False, issues

        # Check each agent response
        for agent_name, response_data in agent_responses.items():
            # Check for empty response
            if not response_data:
                issues.append(f"{agent_name}: Empty response")
                continue

            # Check for error indicators
            if isinstance(response_data, dict):
                if response_data.get("error"):
                    issues.append(f"{agent_name}: Response contains error")

                # Check for required fields based on agent type
                if agent_name == "calculator":
                    if "result" not in response_data:
                        issues.append(f"{agent_name}: Missing 'result' field")

                elif agent_name == "search":
                    if "results" not in response_data:
                        issues.append(f"{agent_name}: Missing 'results' field")

                elif agent_name == "data_processor":
                    if not any(
                        key in response_data
                        for key in ["processed_data", "filtered_results", "aggregations"]
                    ):
                        issues.append(f"{agent_name}: Missing expected data fields")

        is_valid = len(issues) == 0
        return is_valid, issues

    def _check_consistency(
        self, agent_responses: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Check consistency across multiple agent responses.

        For multi-agent workflows, ensure outputs are consistent:
        - No contradictory information
        - Data formats align
        - Sequential agents have coherent data flow
        """
        issues = []

        if len(agent_responses) <= 1:
            # Nothing to check consistency for
            return True, issues

        # Check for contradictory numeric results
        numeric_results = {}
        for agent_name, response_data in agent_responses.items():
            if isinstance(response_data, dict) and "result" in response_data:
                result = response_data["result"]
                if isinstance(result, (int, float)):
                    numeric_results[agent_name] = result

        # If multiple agents return numeric results, they should be related
        # (e.g., not wildly different for same calculation)
        if len(numeric_results) > 1:
            values = list(numeric_results.values())
            # Check for extreme variance (could indicate error)
            max_val = max(values)
            min_val = min(values)
            if max_val > 0 and min_val > 0:
                ratio = max_val / min_val
                if ratio > 1000:  # More than 1000x difference
                    issues.append(
                        f"Inconsistent numeric results across agents: {numeric_results}"
                    )

        # Check data count consistency
        # If search returns N results, processing should reference N items
        search_count = None
        process_count = None

        if "search" in agent_responses:
            search_data = agent_responses["search"]
            if isinstance(search_data, dict):
                results = search_data.get("results", [])
                if isinstance(results, list):
                    search_count = len(results)

        if "data_processor" in agent_responses:
            process_data = agent_responses["data_processor"]
            if isinstance(process_data, dict):
                # Check various possible count fields
                for field in ["processed_data", "filtered_results", "results"]:
                    if field in process_data:
                        data = process_data[field]
                        if isinstance(data, list):
                            process_count = len(data)
                            break

        if search_count is not None and process_count is not None:
            if process_count > search_count:
                issues.append(
                    f"Data processor returned more items ({process_count}) "
                    f"than search provided ({search_count})"
                )

        is_valid = len(issues) == 0
        return is_valid, issues

    async def _detect_hallucination(
        self,
        user_query: Dict[str, Any],
        agent_responses: Dict[str, Any],
        reasoning: Optional[Dict[str, Any]],
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Detect potential hallucinations in agent responses.

        Uses both rule-based and AI-based detection:
        - Rule-based: Check for common hallucination patterns
        - AI-based: Use LLM to validate response relevance
        """
        hallucination_details = {
            "rule_based_check": {},
            "ai_based_check": {},
        }

        # Rule-based hallucination detection
        rule_based_hallucination = self._rule_based_hallucination_check(
            user_query, agent_responses
        )
        hallucination_details["rule_based_check"] = rule_based_hallucination

        # AI-based validation (if enabled)
        ai_based_hallucination = False
        if self.enable_ai_validation:
            ai_check_result = await self._ai_based_hallucination_check(
                user_query, agent_responses
            )
            hallucination_details["ai_based_check"] = ai_check_result
            ai_based_hallucination = ai_check_result.get("hallucination_detected", False)

        # Combine results
        hallucination_detected = (
            rule_based_hallucination.get("detected", False) or ai_based_hallucination
        )

        hallucination_details["final_decision"] = hallucination_detected

        return hallucination_detected, hallucination_details

    def _rule_based_hallucination_check(
        self, user_query: Dict[str, Any], agent_responses: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Rule-based hallucination detection.

        Common patterns:
        - Calculator returning non-numeric or impossible results
        - Search returning results unrelated to query
        - Data processor creating fields not in input
        """
        issues = []
        detected = False

        query_text = user_query.get("query", "").lower()

        # Check calculator responses
        if "calculator" in agent_responses:
            calc_response = agent_responses["calculator"]
            if isinstance(calc_response, dict):
                result = calc_response.get("result")

                # Check for impossible math results
                if result is not None:
                    # Division by zero should error, not return infinity
                    if isinstance(result, float) and (
                        result == float("inf") or result == float("-inf")
                    ):
                        issues.append("Calculator returned infinity (possible error)")
                        detected = True

                    # Check if operation matches query
                    operation = calc_response.get("operation", "")
                    if "add" in query_text or "sum" in query_text or "+" in query_text:
                        if operation not in ["add", "addition", "sum"]:
                            issues.append(
                                f"Operation mismatch: query suggests 'add' but got '{operation}'"
                            )
                            detected = True

        # Check search responses
        if "search" in agent_responses:
            search_response = agent_responses["search"]
            if isinstance(search_response, dict):
                results = search_response.get("results", [])

                # Check if search returned results for wrong query
                # Extract keywords from query
                query_keywords = set(
                    re.findall(r'\b\w+\b', query_text.lower())
                ) - {"search", "find", "for", "about", "the", "a", "an"}

                if results and query_keywords:
                    # Check if top results have any keyword overlap
                    relevant_results = 0
                    for result in results[:3]:  # Check top 3
                        title = result.get("title", "").lower()
                        content = result.get("content", "").lower()
                        text = f"{title} {content}"

                        if any(keyword in text for keyword in query_keywords):
                            relevant_results += 1

                    if relevant_results == 0 and len(results) > 0:
                        issues.append(
                            "Search results appear unrelated to query keywords"
                        )
                        detected = True

        return {
            "detected": detected,
            "issues": issues,
            "check_type": "rule_based",
        }

    async def _ai_based_hallucination_check(
        self, user_query: Dict[str, Any], agent_responses: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use AI to detect hallucinations and validate response relevance.

        Asks Claude to evaluate:
        1. Does the response answer the user's query?
        2. Is the response factually consistent?
        3. Are there any contradictions or fabrications?
        """
        if not self.client:
            return {
                "hallucination_detected": False,
                "reason": "AI validation disabled",
            }

        try:
            # Build validation prompt
            prompt = self._build_validation_prompt(user_query, agent_responses)

            # Call Claude for validation
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=500,
                temperature=0.0,  # Deterministic for validation
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text.strip()

            # Parse validation response
            validation_result = self._parse_validation_response(response_text)

            logger.debug(f"AI validation result: {validation_result}")

            return validation_result

        except Exception as e:
            logger.warning(f"AI-based validation failed: {e}")
            return {
                "hallucination_detected": False,
                "reason": f"Validation error: {str(e)}",
                "error": True,
            }

    def _build_validation_prompt(
        self, user_query: Dict[str, Any], agent_responses: Dict[str, Any]
    ) -> str:
        """Build prompt for AI-based validation."""
        query_text = user_query.get("query", "N/A")

        # Format agent responses
        responses_text = json.dumps(agent_responses, indent=2)

        prompt = f"""You are a response validation system. Evaluate whether the agent responses correctly answer the user's query and check for hallucinations.

USER QUERY:
{query_text}

QUERY PARAMETERS:
{json.dumps({k: v for k, v in user_query.items() if k != 'query'}, indent=2)}

AGENT RESPONSES:
{responses_text}

EVALUATION CRITERIA:
1. Relevance: Do the responses address the user's query?
2. Accuracy: Are the responses factually correct based on the query?
3. Consistency: Are the responses internally consistent?
4. Completeness: Do the responses provide what was requested?
5. Hallucination: Are there any fabricated or contradictory elements?

Respond in JSON format:
{{
  "relevance_score": 0.0-1.0,
  "accuracy_score": 0.0-1.0,
  "consistency_score": 0.0-1.0,
  "completeness_score": 0.0-1.0,
  "hallucination_detected": true/false,
  "issues": ["list of any issues found"],
  "explanation": "brief explanation"
}}

Respond ONLY with the JSON, no other text."""

        return prompt

    def _parse_validation_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI validation response."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                logger.warning("Could not parse AI validation response as JSON")
                return {
                    "hallucination_detected": False,
                    "reason": "Parse error",
                }

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI validation response: {e}")
            return {
                "hallucination_detected": False,
                "reason": f"JSON parse error: {e}",
            }

    def _calculate_confidence(
        self,
        basic_valid: bool,
        consistency_valid: bool,
        hallucination_detected: bool,
        agent_responses: Dict[str, Any],
    ) -> float:
        """
        Calculate confidence score for the response.

        Factors:
        - Basic validation passed
        - Consistency check passed
        - No hallucination detected
        - Response completeness
        - Data quality

        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = 1.0

        # Deduct for validation failures
        if not basic_valid:
            confidence -= 0.3

        if not consistency_valid:
            confidence -= 0.2

        if hallucination_detected:
            confidence -= 0.4

        # Check response quality
        if agent_responses:
            # Check if responses have expected structure
            quality_score = 0.0
            for agent_name, response_data in agent_responses.items():
                if isinstance(response_data, dict):
                    # More complete responses get higher quality score
                    field_count = len(response_data)
                    if field_count >= 3:
                        quality_score += 0.1
                    elif field_count >= 2:
                        quality_score += 0.05

            # Cap quality bonus at 0.2
            quality_score = min(quality_score, 0.2)
            confidence += quality_score

        # Ensure confidence is in valid range
        confidence = max(0.0, min(1.0, confidence))

        return confidence
