"""
Security utilities for input validation and sanitization.

This module provides functions to validate and sanitize inputs to prevent
security vulnerabilities like injection attacks and path traversal.
"""

import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised when security validation fails."""
    pass


class RateLimiter:
    """
    Rate limiter to prevent abuse and DoS attacks.
    Tracks requests per IP/identifier with sliding window.
    """
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.blocked: Dict[str, float] = {}  # identifier -> unblock_time
        
    def is_allowed(self, identifier: str) -> bool:
        """
        Check if request is allowed for identifier.
        
        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            
        Returns:
            True if request allowed, False if rate limited
        """
        now = time.time()
        
        # Check if currently blocked
        if identifier in self.blocked:
            if now < self.blocked[identifier]:
                logger.warning(f"Rate limit: {identifier} is blocked until {self.blocked[identifier]}")
                return False
            else:
                # Unblock expired
                del self.blocked[identifier]
        
        # Get request history for this identifier
        request_times = self.requests[identifier]
        
        # Remove requests outside the window
        cutoff = now - self.window_seconds
        request_times = [t for t in request_times if t > cutoff]
        self.requests[identifier] = request_times
        
        # Check if limit exceeded
        if len(request_times) >= self.max_requests:
            # Block for window duration
            self.blocked[identifier] = now + self.window_seconds
            logger.warning(
                f"Rate limit exceeded: {identifier} blocked for {self.window_seconds}s "
                f"({len(request_times)} requests in {self.window_seconds}s)"
            )
            return False
        
        # Record this request
        request_times.append(now)
        return True
    
    def reset(self, identifier: str) -> None:
        """Reset rate limit for identifier."""
        if identifier in self.requests:
            del self.requests[identifier]
        if identifier in self.blocked:
            del self.blocked[identifier]


# Global rate limiter instance
_rate_limiter = RateLimiter(max_requests=100, window_seconds=60)


def check_rate_limit(identifier: str) -> None:
    """
    Check rate limit for identifier.
    
    Args:
        identifier: Unique identifier for rate limiting
        
    Raises:
        SecurityError: If rate limit exceeded
    """
    if not _rate_limiter.is_allowed(identifier):
        raise SecurityError(f"Rate limit exceeded for {identifier}")


def detect_prompt_injection(text: str) -> bool:
    """
    Detect common prompt injection patterns.
    
    Args:
        text: Text to analyze
        
    Returns:
        True if injection detected, False otherwise
    """
    text_lower = text.lower()
    
    # Prompt injection patterns
    injection_patterns = [
        # Role manipulation
        r'ignore (all )?previous (instructions|prompts|rules)',
        r'disregard (all )?(prior|previous|above) (instructions|prompts|context)',
        r'forget (all )?(previous|prior) (instructions|context)',
        r'you are now',
        r'your new (role|purpose|instructions) (is|are)',
        r'system[:;\s]',
        r'<\s*system\s*>',
        
        # Instruction override
        r'instead,?\s+(do|say|respond|tell|give)',
        r'but actually',
        r'real (task|instruction|purpose)',
        r'hidden (instruction|prompt|purpose)',
        
        # Developer mode / jailbreak
        r'developer mode',
        r'admin mode',
        r'god mode',
        r'jailbreak',
        r'bypass (all )?(restrictions|filters|safety)',
        r'disable (all )?(safety|filters|restrictions)',
        
        # Direct prompt leakage attempts
        r'show me (your|the) (system )?(prompt|instructions)',
        r'what (is|are) your (system )?(prompt|instructions)',
        r'reveal (your )?(system )?(prompt|instructions)',
        r'print (your )?(system )?(prompt|instructions)',
        
        # End-of-prompt markers
        r'<\|endoftext\|>',
        r'<\|im_end\|>',
        r'###\s*$',
        
        # Code execution attempts in prompts
        r'exec\s*\(',
        r'eval\s*\(',
        r'__import__\s*\(',
        r'compile\s*\(',
        
        # Multiple role/persona changes
        r'(act|pretend|imagine|roleplay) (as|like|that you are)',
    ]
    
    for pattern in injection_patterns:
        if re.search(pattern, text_lower):
            logger.warning(f"Prompt injection pattern detected: {pattern}")
            return True
    
    # Check for excessive special characters (obfuscation attempt)
    special_char_ratio = sum(1 for c in text if not c.isalnum() and not c.isspace()) / max(len(text), 1)
    if special_char_ratio > 0.4:
        logger.warning(f"Excessive special characters detected: {special_char_ratio:.2%}")
        return True
    
    # Check for very long repeated patterns (potential overflow)
    repeated_pattern = re.search(r'(.{10,})\1{5,}', text)
    if repeated_pattern:
        logger.warning("Repeated pattern detected (potential overflow attack)")
        return True
    
    return False


def detect_xss_patterns(text: str) -> bool:
    """
    Detect Cross-Site Scripting (XSS) patterns.
    
    Args:
        text: Text to analyze
        
    Returns:
        True if XSS patterns detected, False otherwise
    """
    xss_patterns = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=\s*["\']',  # Event handlers
        r'<iframe',
        r'<object',
        r'<embed',
        r'<svg[^>]*>.*?</svg>',
        r'vbscript:',
        r'data:text/html',
    ]
    
    for pattern in xss_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(f"XSS pattern detected: {pattern}")
            return True
    
    return False


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
    
    # Check for prompt injection
    if detect_prompt_injection(sanitized):
        logger.error("Prompt injection attempt detected and blocked")
        raise SecurityError("Input contains potentially malicious patterns")
    
    # Check for XSS patterns
    if detect_xss_patterns(sanitized):
        logger.error("XSS pattern detected and blocked")
        raise SecurityError("Input contains potentially malicious HTML/JavaScript")

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
        r'\bwget\b',  # wget command
        r'\bcurl\b',  # curl command
        r'\brm\s+-rf',  # Dangerous delete
        r'\bmkdir\b',  # Directory creation
        r'\bchmod\b',  # Permission changes
        r'\bchown\b',  # Ownership changes
        r'/etc/passwd',  # Sensitive file access
        r'/etc/shadow',  # Sensitive file access
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, value):
            logger.warning(f"Command injection pattern detected: {pattern}")
            raise SecurityError(f"Potentially dangerous command pattern detected")


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
        r"(;\s*INSERT\s+)",  # INSERT statements
        r"(UNION\s+SELECT)",  # UNION-based injection
        r"(xp_cmdshell)",  # SQL Server command execution
        r"(exec\s*\()",  # Execute functions
        r"(sp_executesql)",  # SQL Server stored proc
        r"(INTO\s+OUTFILE)",  # File writing
        r"(LOAD_FILE)",  # File reading
        r"(0x[0-9a-f]+)",  # Hex-encoded strings
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
    check_rate_limit: bool = False,
    identifier: Optional[str] = None,
) -> None:
    """
    Comprehensive input validation.

    Args:
        data: Input data to validate
        check_command_injection: Check for command injection
        check_sql_injection: Check for SQL injection
        check_size: Check input size limits
        max_size_bytes: Maximum size in bytes
        check_rate_limit: Check rate limiting
        identifier: Identifier for rate limiting (required if check_rate_limit=True)

    Raises:
        SecurityError: If validation fails
    """
    # Check rate limit
    if check_rate_limit:
        if not identifier:
            raise ValueError("identifier required when check_rate_limit=True")
        check_rate_limit(identifier)
    
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


def sanitize_output(data: Any, remove_sensitive: bool = True) -> Any:
    """
    Sanitize output data before returning to user.
    Removes sensitive information and ensures safe content.
    
    Args:
        data: Data to sanitize
        remove_sensitive: Whether to remove sensitive information
        
    Returns:
        Sanitized data
    """
    if isinstance(data, str):
        # Remove potential XSS
        sanitized = re.sub(r'<script[^>]*>.*?</script>', '', data, flags=re.IGNORECASE | re.DOTALL)
        sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'on\w+\s*=', '', sanitized, flags=re.IGNORECASE)
        
        if remove_sensitive:
            # Remove potential sensitive patterns
            sanitized = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', sanitized)
            sanitized = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', sanitized)
            sanitized = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD]', sanitized)
            sanitized = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', sanitized)
            
        return sanitized
        
    elif isinstance(data, dict):
        return {k: sanitize_output(v, remove_sensitive) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_output(item, remove_sensitive) for item in data]
    else:
        return data


def validate_json_schema(data: Dict[str, Any], allowed_keys: Set[str]) -> None:
    """
    Validate that JSON data only contains allowed keys.
    
    Args:
        data: Data to validate
        allowed_keys: Set of allowed key names
        
    Raises:
        SecurityError: If unexpected keys found
    """
    unexpected_keys = set(data.keys()) - allowed_keys
    if unexpected_keys:
        logger.warning(f"Unexpected keys in input: {unexpected_keys}")
        raise SecurityError(f"Input contains unexpected keys: {unexpected_keys}")


def detect_encoding_attacks(text: str) -> bool:
    """
    Detect encoding-based obfuscation attacks.
    
    Args:
        text: Text to analyze
        
    Returns:
        True if encoding attack detected
    """
    # Check for URL encoding obfuscation
    url_encoded_count = text.count('%')
    if url_encoded_count > len(text) * 0.2:
        logger.warning(f"Excessive URL encoding detected: {url_encoded_count} instances")
        return True
    
    # Check for unicode obfuscation
    unicode_pattern = r'\\u[0-9a-fA-F]{4}'
    unicode_count = len(re.findall(unicode_pattern, text))
    if unicode_count > 10:
        logger.warning(f"Excessive unicode encoding detected: {unicode_count} instances")
        return True
    
    # Check for base64-like patterns (long alphanumeric strings)
    base64_pattern = r'[A-Za-z0-9+/]{50,}={0,2}'
    if re.search(base64_pattern, text):
        logger.warning("Potential base64 encoded content detected")
        return True
    
    return False


def create_security_report(query: str, validation_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a security validation report.
    
    Args:
        query: Original query
        validation_results: Results from various security checks
        
    Returns:
        Security report dictionary
    """
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "query_length": len(query),
        "checks_performed": list(validation_results.keys()),
        "passed": all(validation_results.values()),
        "details": validation_results,
        "risk_level": "high" if not all(validation_results.values()) else "low"
    }


# Export key functions
__all__ = [
    'SecurityError',
    'RateLimiter',
    'sanitize_string',
    'sanitize_dict',
    'sanitize_output',
    'validate_no_command_injection',
    'validate_no_sql_injection',
    'validate_path',
    'validate_input',
    'validate_input_size',
    'validate_json_schema',
    'detect_prompt_injection',
    'detect_xss_patterns',
    'detect_encoding_attacks',
    'check_rate_limit',
    'get_safe_env_var',
    'create_security_report',
]
