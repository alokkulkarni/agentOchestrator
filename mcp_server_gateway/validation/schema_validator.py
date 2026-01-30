"""
JSON Schema validation for agent outputs.

This module provides validation of agent outputs against JSON schemas
to ensure structured data meets expected format requirements.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import jsonschema
from jsonschema import Draft7Validator, validators

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


class SchemaValidator:
    """
    JSON Schema validator for agent outputs.

    Loads and validates outputs against JSON Schema definitions,
    providing detailed error messages for validation failures.
    """

    def __init__(self, schemas_path: str | Path):
        """
        Initialize schema validator.

        Args:
            schemas_path: Directory containing JSON schema files
        """
        self.schemas_path = Path(schemas_path)
        self._schemas: Dict[str, Dict[str, Any]] = {}

        # Load all schemas from directory
        self._load_schemas()

        logger.info(
            f"Schema validator initialized with {len(self._schemas)} schemas "
            f"from {self.schemas_path}"
        )

    def _load_schemas(self) -> None:
        """Load all JSON schema files from schemas directory."""
        if not self.schemas_path.exists():
            logger.warning(f"Schemas path does not exist: {self.schemas_path}")
            return

        if not self.schemas_path.is_dir():
            logger.warning(f"Schemas path is not a directory: {self.schemas_path}")
            return

        # Load all .json files
        for schema_file in self.schemas_path.glob("*.json"):
            try:
                with open(schema_file, 'r', encoding='utf-8') as f:
                    schema = json.load(f)

                # Use filename (without extension) as schema name
                schema_name = schema_file.stem
                self._schemas[schema_name] = schema

                logger.debug(f"Loaded schema: {schema_name}")

            except Exception as e:
                logger.error(f"Failed to load schema {schema_file}: {e}")

    def validate(
        self,
        data: Dict[str, Any],
        schema_name: str,
        strict: bool = False,
    ) -> tuple[bool, List[str]]:
        """
        Validate data against a schema.

        Args:
            data: Data to validate
            schema_name: Name of schema to validate against
            strict: If True, raise exception on validation error

        Returns:
            Tuple of (is_valid, list of error messages)

        Raises:
            ValidationError: If strict=True and validation fails
            KeyError: If schema_name not found
        """
        if schema_name not in self._schemas:
            available = ", ".join(self._schemas.keys())
            error_msg = (
                f"Schema '{schema_name}' not found. "
                f"Available schemas: {available}"
            )
            logger.error(error_msg)
            if strict:
                raise KeyError(error_msg)
            return False, [error_msg]

        schema = self._schemas[schema_name]

        try:
            # Validate against schema
            validator = Draft7Validator(schema)
            errors = list(validator.iter_errors(data))

            if errors:
                error_messages = []
                for error in errors:
                    # Format error path
                    path = " -> ".join(str(p) for p in error.path) if error.path else "root"
                    message = f"{path}: {error.message}"
                    error_messages.append(message)

                logger.warning(
                    f"Validation failed for schema '{schema_name}': "
                    f"{len(errors)} error(s)"
                )

                if strict:
                    raise ValidationError(
                        f"Validation failed:\n" + "\n".join(error_messages)
                    )

                return False, error_messages
            else:
                logger.debug(f"Validation successful for schema '{schema_name}'")
                return True, []

        except jsonschema.SchemaError as e:
            error_msg = f"Invalid schema '{schema_name}': {e}"
            logger.error(error_msg)
            if strict:
                raise ValidationError(error_msg) from e
            return False, [error_msg]

    def validate_required_fields(
        self,
        data: Dict[str, Any],
        required_fields: List[str],
        strict: bool = False,
    ) -> tuple[bool, List[str]]:
        """
        Validate that data contains required fields.

        Args:
            data: Data to validate
            required_fields: List of required field names
            strict: If True, raise exception on validation error

        Returns:
            Tuple of (is_valid, list of missing fields)

        Raises:
            ValidationError: If strict=True and validation fails
        """
        missing_fields = []

        for field in required_fields:
            # Support nested fields with dot notation
            keys = field.split(".")
            value = data

            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    missing_fields.append(field)
                    break

        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            logger.warning(error_msg)

            if strict:
                raise ValidationError(error_msg)

            return False, missing_fields

        logger.debug("All required fields present")
        return True, []

    def has_schema(self, schema_name: str) -> bool:
        """
        Check if a schema exists.

        Args:
            schema_name: Name of schema to check

        Returns:
            True if schema exists
        """
        return schema_name in self._schemas

    def get_schema(self, schema_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a schema by name.

        Args:
            schema_name: Name of schema

        Returns:
            Schema dictionary or None if not found
        """
        return self._schemas.get(schema_name)

    def list_schemas(self) -> List[str]:
        """
        Get list of available schema names.

        Returns:
            List of schema names
        """
        return list(self._schemas.keys())

    def reload_schemas(self) -> None:
        """Reload all schemas from disk."""
        logger.info("Reloading schemas")
        self._schemas.clear()
        self._load_schemas()

    def infer_schema(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Infer a basic JSON schema from data structure.

        Useful for untyped outputs or creating schema templates.

        Args:
            data: Data to infer schema from

        Returns:
            Inferred JSON schema
        """
        def infer_type(value: Any) -> Dict[str, Any]:
            """Infer JSON schema type from Python value."""
            if value is None:
                return {"type": "null"}
            elif isinstance(value, bool):
                return {"type": "boolean"}
            elif isinstance(value, int):
                return {"type": "integer"}
            elif isinstance(value, float):
                return {"type": "number"}
            elif isinstance(value, str):
                return {"type": "string"}
            elif isinstance(value, list):
                if value:
                    # Infer from first element
                    return {
                        "type": "array",
                        "items": infer_type(value[0])
                    }
                else:
                    return {"type": "array"}
            elif isinstance(value, dict):
                properties = {}
                required = []
                for k, v in value.items():
                    properties[k] = infer_type(v)
                    required.append(k)
                return {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            else:
                return {"type": "string"}  # Fallback

        schema = infer_type(data)
        schema["$schema"] = "http://json-schema.org/draft-07/schema#"

        return schema
