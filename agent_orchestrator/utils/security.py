"""
Security utilities for input validation and sanitization.

This module provides functions to validate and sanitize inputs to prevent
security vulnerabilities like injection attacks and path traversal.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised when security validation fails."""
    pass


def sanitize_string(value: str, max_length: int = 10000) -> str:
    """
    Sanitize string input by removing dangerous characters.

    Args:
        value: String to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string

    Raises:
        SecurityError: If input is too long
    """
    if len(value) > max_length:
        raise SecurityError(f"Input too long: {len(value)} > {max_length}")

    # Remove null bytes and control characters
    sanitized = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', value)

    return sanitized


def validate_no_command_injection(value: str) -> None:
    """
    Validate that input doesn't contain command injection patterns.

    Args:
        value: String to validate

    Raises:
        SecurityError: If dangerous patterns detected
    """
    dangerous_patterns = [
        r';\s*\w+',  # Command chaining with semicolon
        r'\|\s*\w+',  # Pipe to another command
        r'&&\s*\w+',  # AND command chaining
        r'\|\|',  # OR command chaining
        r'`.*`',  # Backtick command substitution
        r'\$\(.*\)',  # Command substitution
        r'<\(.*\)',  # Process substitution
        r'>\(.*\)',  # Process substitution
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, value):
            logger.warning(f"Command injection pattern detected: {pattern}")
            raise SecurityError(f"Potentially dangerous input detected")


def validate_path(path: str, allowed_base: Optional[str] = None) -> Path:
    """
    Validate file path to prevent path traversal attacks.

    Args:
        path: Path to validate
        allowed_base: Optional base directory that path must be within

    Returns:
        Validated Path object

    Raises:
        SecurityError: If path is invalid or outside allowed base
    """
    # Convert to Path and resolve
    try:
        path_obj = Path(path).resolve()
    except (ValueError, RuntimeError) as e:
        raise SecurityError(f"Invalid path: {e}")

    # Check for path traversal
    if ".." in path:
        raise SecurityError("Path traversal detected")

    # Check against allowed base if specified
    if allowed_base:
        try:
            base_path = Path(allowed_base).resolve()
            if not str(path_obj).startswith(str(base_path)):
                raise SecurityError(f"Path outside allowed base: {path_obj}")
        except (ValueError, RuntimeError) as e:
            raise SecurityError(f"Invalid base path: {e}")

    return path_obj


def validate_input_size(data: Dict[str, Any], max_size_bytes: int = 1_000_000) -> None:
    """
    Validate that input data size is within limits.

    Args:
        data: Input data to validate
        max_size_bytes: Maximum size in bytes

    Raises:
        SecurityError: If data is too large
    """
    import json
    import sys

    # Estimate size by serializing to JSON
    try:
        json_str = json.dumps(data)
        size = sys.getsizeof(json_str)

        if size > max_size_bytes:
            raise SecurityError(
                f"Input data too large: {size} bytes > {max_size_bytes} bytes"
            )
    except (TypeError, ValueError) as e:
        logger.warning(f"Could not validate input size: {e}")


def validate_no_sql_injection(value: str) -> None:
    """
    Validate that input doesn't contain SQL injection patterns.

    Args:
        value: String to validate

    Raises:
        SecurityError: If SQL injection patterns detected
    """
    sql_patterns = [
        r"('\s*(OR|AND)\s*'?\d*'?\s*=\s*'?\d*)",  # Basic SQL injection
        r"(--|\#|/\*|\*/)",  # SQL comments
        r"(;\s*DROP\s+)",  # DROP statements
        r"(;\s*DELETE\s+)",  # DELETE statements
        r"(;\s*UPDATE\s+)",  # UPDATE statements
        r"(UNION\s+SELECT)",  # UNION-based injection
        r"(xp_cmdshell)",  # SQL Server command execution
    ]

    value_upper = value.upper()

    for pattern in sql_patterns:
        if re.search(pattern, value_upper, re.IGNORECASE):
            logger.warning(f"SQL injection pattern detected: {pattern}")
            raise SecurityError("Potentially dangerous SQL pattern detected")


def sanitize_dict(
    data: Dict[str, Any],
    max_depth: int = 10,
    current_depth: int = 0,
) -> Dict[str, Any]:
    """
    Recursively sanitize dictionary values.

    Args:
        data: Dictionary to sanitize
        max_depth: Maximum nesting depth
        current_depth: Current recursion depth

    Returns:
        Sanitized dictionary

    Raises:
        SecurityError: If max depth exceeded
    """
    if current_depth > max_depth:
        raise SecurityError(f"Max nesting depth exceeded: {max_depth}")

    sanitized = {}

    for key, value in data.items():
        # Sanitize key
        if not isinstance(key, str):
            key = str(key)
        key = sanitize_string(key, max_length=1000)

        # Sanitize value based on type
        if isinstance(value, str):
            sanitized[key] = sanitize_string(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value, max_depth, current_depth + 1)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_dict(item, max_depth, current_depth + 1)
                if isinstance(item, dict)
                else sanitize_string(str(item))
                if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            sanitized[key] = value

    return sanitized


def validate_input(
    data: Dict[str, Any],
    check_command_injection: bool = True,
    check_sql_injection: bool = False,
    check_size: bool = True,
    max_size_bytes: int = 1_000_000,
) -> None:
    """
    Comprehensive input validation.

    Args:
        data: Input data to validate
        check_command_injection: Check for command injection
        check_sql_injection: Check for SQL injection
        check_size: Check input size limits
        max_size_bytes: Maximum size in bytes

    Raises:
        SecurityError: If validation fails
    """
    # Check size
    if check_size:
        validate_input_size(data, max_size_bytes)

    # Recursively check string values
    def check_strings(obj: Any) -> None:
        if isinstance(obj, str):
            if check_command_injection:
                validate_no_command_injection(obj)
            if check_sql_injection:
                validate_no_sql_injection(obj)
        elif isinstance(obj, dict):
            for value in obj.values():
                check_strings(value)
        elif isinstance(obj, list):
            for item in obj:
                check_strings(item)

    check_strings(data)


def get_safe_env_var(name: str, default: str = "") -> str:
    """
    Safely get environment variable.

    Args:
        name: Environment variable name
        default: Default value if not found

    Returns:
        Environment variable value or default
    """
    import os

    value = os.getenv(name, default)

    # Sanitize the value
    if value:
        value = sanitize_string(value, max_length=10000)

    return value
