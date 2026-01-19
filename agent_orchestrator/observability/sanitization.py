"""
PII sanitization for Agent Orchestrator logs.

Redacts sensitive information from logs to prevent data leaks:
- API keys and tokens
- Emails and phone numbers
- Personally identifiable information
"""

import re
from typing import Any, Dict, List, Union


# Compiled patterns for common PII
PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", re.IGNORECASE),
    "phone": re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"),
    "api_key_anthropic": re.compile(r"sk-ant-[a-zA-Z0-9-]{95,}"),
    "api_key_openai": re.compile(r"sk-[a-zA-Z0-9]{48,}"),
    "bearer_token": re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}

# Sensitive field names (always redacted)
SENSITIVE_KEYS = {
    "api_key", "apikey", "secret", "password", "token",
    "authorization", "auth", "credential", "private_key",
    "access_key", "secret_key",
}


def sanitize_text(text: str, redaction_text: str = "[REDACTED]") -> str:
    """
    Sanitize text by redacting sensitive patterns.

    Args:
        text: Text to sanitize
        redaction_text: Replacement text

    Returns:
        Sanitized text
    """
    if not text or not isinstance(text, str):
        return text

    sanitized = text
    for pattern_name, pattern in PATTERNS.items():
        # Partial redaction for some patterns (show first/last chars)
        if pattern_name in ["email", "api_key_anthropic"]:
            def replace_partial(match):
                matched = match.group(0)
                if len(matched) <= 8:
                    return redaction_text
                return f"{matched[:4]}...{matched[-4:]}"
            sanitized = pattern.sub(replace_partial, sanitized)
        else:
            sanitized = pattern.sub(f"{redaction_text}_{pattern_name.upper()}", sanitized)

    return sanitized


def sanitize_dict(data: Dict[str, Any], deep: bool = True) -> Dict[str, Any]:
    """
    Sanitize dictionary by redacting sensitive keys and values.

    Args:
        data: Dictionary to sanitize
        deep: If True, recursively sanitize nested dicts

    Returns:
        Sanitized dictionary
    """
    if not data or not isinstance(data, dict):
        return data

    sanitized = {}
    for key, value in data.items():
        # Check if key is sensitive
        if any(sensitive in key.lower() for sensitive in SENSITIVE_KEYS):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, str):
            sanitized[key] = sanitize_text(value)
        elif isinstance(value, dict) and deep:
            sanitized[key] = sanitize_dict(value, deep)
        elif isinstance(value, list) and deep:
            sanitized[key] = [
                sanitize_dict(item, deep) if isinstance(item, dict)
                else sanitize_text(item) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            sanitized[key] = value

    return sanitized


def sanitize_data(
    data: Union[str, Dict, List],
    max_length: int = 1000
) -> Union[str, Dict, List]:
    """
    Sanitize data for logging with length limits.

    Args:
        data: Data to sanitize
        max_length: Maximum length for string values

    Returns:
        Sanitized data
    """
    if isinstance(data, str):
        sanitized = sanitize_text(data)
        if len(sanitized) > max_length:
            return sanitized[:max_length] + "... [truncated]"
        return sanitized
    elif isinstance(data, dict):
        sanitized = sanitize_dict(data)
        # Truncate long string values
        for key, value in sanitized.items():
            if isinstance(value, str) and len(value) > max_length:
                sanitized[key] = value[:max_length] + "... [truncated]"
        return sanitized
    elif isinstance(data, list):
        return [sanitize_data(item, max_length) for item in data]
    else:
        return data
