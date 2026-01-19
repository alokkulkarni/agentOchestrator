"""
Content sanitization for PII and sensitive data redaction.

Provides utilities to sanitize:
- Email addresses
- Phone numbers
- API keys and tokens
- Credit card numbers
- SSN and other identifiers
- IP addresses
- Custom patterns
"""

import re
from typing import List, Dict, Any, Optional, Union


class ContentSanitizer:
    """Sanitizes content by redacting PII and sensitive information."""

    def __init__(self, custom_patterns: Optional[Dict[str, str]] = None):
        """
        Initialize content sanitizer.

        Args:
            custom_patterns: Additional regex patterns to redact
                Format: {"pattern_name": "regex_pattern"}
        """
        # Default patterns for common PII
        self.patterns = {
            # Email addresses
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            # Phone numbers (various formats)
            "phone": r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
            # API keys (common patterns)
            "api_key_anthropic": r"sk-ant-[a-zA-Z0-9-]{95,}",
            "api_key_openai": r"sk-[a-zA-Z0-9]{48,}",
            "api_key_generic": r"[a-zA-Z0-9_-]{32,}",
            # AWS keys
            "aws_access_key": r"AKIA[0-9A-Z]{16}",
            "aws_secret_key": r"[A-Za-z0-9/+=]{40}",
            # Bearer tokens
            "bearer_token": r"Bearer\s+[A-Za-z0-9\-._~+/]+=*",
            # Credit card numbers (basic pattern)
            "credit_card": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
            # SSN
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
            # IP addresses
            "ipv4": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "ipv6": r"\b(?:[A-F0-9]{1,4}:){7}[A-F0-9]{1,4}\b",
            # JWT tokens
            "jwt": r"eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*",
        }

        # Add custom patterns
        if custom_patterns:
            self.patterns.update(custom_patterns)

        # Compile patterns for efficiency
        self.compiled_patterns = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.patterns.items()
        }

        # Redaction settings
        self.redaction_text = "[REDACTED]"
        self.partial_redaction = True  # Show first/last chars

    def sanitize_text(
        self,
        text: str,
        patterns_to_apply: Optional[List[str]] = None,
        preserve_length: bool = False,
    ) -> str:
        """
        Sanitize text by redacting sensitive patterns.

        Args:
            text: Text to sanitize
            patterns_to_apply: List of pattern names to apply (None = all)
            preserve_length: If True, replace with asterisks of same length

        Returns:
            Sanitized text
        """
        if not text:
            return text

        sanitized = text

        # Determine which patterns to use
        patterns_to_use = patterns_to_apply or list(self.compiled_patterns.keys())

        for pattern_name in patterns_to_use:
            if pattern_name not in self.compiled_patterns:
                continue

            pattern = self.compiled_patterns[pattern_name]

            if preserve_length:
                # Replace with asterisks of same length
                def replace_preserve(match):
                    return "*" * len(match.group(0))

                sanitized = pattern.sub(replace_preserve, sanitized)
            elif self.partial_redaction and pattern_name in [
                "email",
                "phone",
                "api_key_anthropic",
            ]:
                # Partial redaction (show first/last few chars)
                def replace_partial(match):
                    text = match.group(0)
                    if len(text) <= 8:
                        return self.redaction_text
                    return f"{text[:4]}...{text[-4:]}"

                sanitized = pattern.sub(replace_partial, sanitized)
            else:
                # Full redaction
                sanitized = pattern.sub(
                    f"{self.redaction_text}_{pattern_name.upper()}", sanitized
                )

        return sanitized

    def sanitize_dict(
        self,
        data: Dict[str, Any],
        keys_to_sanitize: Optional[List[str]] = None,
        deep: bool = True,
    ) -> Dict[str, Any]:
        """
        Sanitize dictionary by redacting sensitive keys and values.

        Args:
            data: Dictionary to sanitize
            keys_to_sanitize: List of key names to always redact (case-insensitive)
            deep: If True, recursively sanitize nested dicts

        Returns:
            Sanitized dictionary
        """
        if not data:
            return data

        # Default sensitive keys
        sensitive_keys = {
            "api_key",
            "apikey",
            "secret",
            "password",
            "token",
            "authorization",
            "auth",
            "credential",
            "private_key",
            "access_key",
            "secret_key",
        }

        if keys_to_sanitize:
            sensitive_keys.update(k.lower() for k in keys_to_sanitize)

        sanitized = {}

        for key, value in data.items():
            # Check if key is sensitive
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = self.redaction_text
            elif isinstance(value, str):
                # Sanitize string values
                sanitized[key] = self.sanitize_text(value)
            elif isinstance(value, dict) and deep:
                # Recursively sanitize nested dicts
                sanitized[key] = self.sanitize_dict(value, keys_to_sanitize, deep)
            elif isinstance(value, list) and deep:
                # Sanitize list items
                sanitized[key] = [
                    (
                        self.sanitize_dict(item, keys_to_sanitize, deep)
                        if isinstance(item, dict)
                        else (
                            self.sanitize_text(item)
                            if isinstance(item, str)
                            else item
                        )
                    )
                    for item in value
                ]
            else:
                sanitized[key] = value

        return sanitized

    def sanitize_message(
        self, message: Dict[str, Any], sanitize_content: bool = False
    ) -> Dict[str, Any]:
        """
        Sanitize a chat message for logging.

        Args:
            message: Message dictionary with 'role' and 'content'
            sanitize_content: If True, also sanitize message content

        Returns:
            Sanitized message
        """
        sanitized = message.copy()

        if sanitize_content and "content" in sanitized:
            sanitized["content"] = self.sanitize_text(sanitized["content"])

        return sanitized

    def sanitize_messages(
        self, messages: List[Dict[str, Any]], sanitize_content: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Sanitize a list of chat messages.

        Args:
            messages: List of message dicts
            sanitize_content: If True, sanitize message content

        Returns:
            List of sanitized messages
        """
        return [self.sanitize_message(msg, sanitize_content) for msg in messages]

    def sanitize_for_logging(
        self, data: Union[str, Dict, List], max_length: int = 500
    ) -> Union[str, Dict, List]:
        """
        Sanitize data for logging with length limits.

        Args:
            data: Data to sanitize
            max_length: Maximum length for string values

        Returns:
            Sanitized and truncated data
        """
        if isinstance(data, str):
            sanitized = self.sanitize_text(data)
            if len(sanitized) > max_length:
                return sanitized[:max_length] + "... [truncated]"
            return sanitized
        elif isinstance(data, dict):
            sanitized = self.sanitize_dict(data)
            # Truncate long string values
            for key, value in sanitized.items():
                if isinstance(value, str) and len(value) > max_length:
                    sanitized[key] = value[:max_length] + "... [truncated]"
            return sanitized
        elif isinstance(data, list):
            return [self.sanitize_for_logging(item, max_length) for item in data]
        else:
            return data

    def redact_api_response(
        self, response: Dict[str, Any], include_usage: bool = True
    ) -> Dict[str, Any]:
        """
        Redact API response for safe logging.

        Args:
            response: API response dictionary
            include_usage: If True, include usage stats

        Returns:
            Redacted response with metadata only
        """
        safe_response = {
            "model": response.get("model", "unknown"),
            "provider": response.get("provider", "unknown"),
            "finish_reason": response.get("finish_reason", "unknown"),
        }

        if include_usage:
            safe_response["usage"] = response.get("usage", {})

        # Optionally include content length instead of actual content
        if "content" in response:
            safe_response["content_length"] = len(response["content"])
            # Include first 50 chars sanitized
            safe_response["content_preview"] = self.sanitize_text(
                response["content"][:50]
            )

        return safe_response

    def add_pattern(self, name: str, pattern: str):
        """
        Add a custom redaction pattern.

        Args:
            name: Pattern name
            pattern: Regex pattern string
        """
        self.patterns[name] = pattern
        self.compiled_patterns[name] = re.compile(pattern, re.IGNORECASE)

    def remove_pattern(self, name: str):
        """
        Remove a redaction pattern.

        Args:
            name: Pattern name to remove
        """
        if name in self.patterns:
            del self.patterns[name]
        if name in self.compiled_patterns:
            del self.compiled_patterns[name]

    def set_redaction_text(self, text: str):
        """
        Set the redaction replacement text.

        Args:
            text: Text to use for redaction
        """
        self.redaction_text = text

    def enable_partial_redaction(self, enabled: bool = True):
        """
        Enable or disable partial redaction.

        Args:
            enabled: Whether to show partial content
        """
        self.partial_redaction = enabled


# Global sanitizer instance
_sanitizer: Optional[ContentSanitizer] = None


def get_sanitizer() -> ContentSanitizer:
    """
    Get global sanitizer instance.

    Returns:
        ContentSanitizer instance
    """
    global _sanitizer
    if _sanitizer is None:
        _sanitizer = ContentSanitizer()
    return _sanitizer


def sanitize_content(
    content: Union[str, Dict, List],
    sanitize_text_content: bool = False,
    max_length: int = 500,
) -> Union[str, Dict, List]:
    """
    Convenience function to sanitize content for logging.

    Args:
        content: Content to sanitize
        sanitize_text_content: Whether to sanitize text content
        max_length: Maximum length for strings

    Returns:
        Sanitized content
    """
    sanitizer = get_sanitizer()

    if isinstance(content, str):
        return sanitizer.sanitize_text(content) if sanitize_text_content else content
    elif isinstance(content, dict):
        return sanitizer.sanitize_dict(content)
    elif isinstance(content, list):
        return [sanitize_content(item, sanitize_text_content, max_length) for item in content]
    else:
        return content
