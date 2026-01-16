"""Tests for validation and formatting."""

import json

import pytest

from agent_orchestrator.agents import AgentResponse
from agent_orchestrator.validation import OutputFormatter, SchemaValidator


class TestSchemaValidator:
    """Test JSON schema validation."""

    def test_validator_initialization(self, tmp_path):
        """Test validator initialization."""
        # Create temporary schemas directory
        schemas_dir = tmp_path / "schemas"
        schemas_dir.mkdir()

        # Create a simple schema
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["result"],
            "properties": {
                "result": {"type": "number"}
            }
        }

        schema_file = schemas_dir / "test_schema.json"
        with open(schema_file, 'w') as f:
            json.dump(schema, f)

        validator = SchemaValidator(schemas_dir)

        assert validator.has_schema("test_schema")
        assert "test_schema" in validator.list_schemas()

    def test_validate_success(self, tmp_path):
        """Test successful validation."""
        schemas_dir = tmp_path / "schemas"
        schemas_dir.mkdir()

        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["result"],
            "properties": {
                "result": {"type": "number"}
            }
        }

        with open(schemas_dir / "calc.json", 'w') as f:
            json.dump(schema, f)

        validator = SchemaValidator(schemas_dir)

        data = {"result": 42}
        is_valid, errors = validator.validate(data, "calc")

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_failure(self, tmp_path):
        """Test validation failure."""
        schemas_dir = tmp_path / "schemas"
        schemas_dir.mkdir()

        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["result"],
            "properties": {
                "result": {"type": "number"}
            }
        }

        with open(schemas_dir / "calc.json", 'w') as f:
            json.dump(schema, f)

        validator = SchemaValidator(schemas_dir)

        # Invalid data (missing required field)
        data = {"other": "value"}
        is_valid, errors = validator.validate(data, "calc")

        assert is_valid is False
        assert len(errors) > 0

    def test_validate_required_fields(self, tmp_path):
        """Test required fields validation."""
        validator = SchemaValidator(tmp_path)

        data = {"field1": "value1", "field2": "value2"}
        is_valid, missing = validator.validate_required_fields(
            data,
            required_fields=["field1", "field2"]
        )

        assert is_valid is True
        assert len(missing) == 0

        is_valid, missing = validator.validate_required_fields(
            data,
            required_fields=["field1", "field3"]
        )

        assert is_valid is False
        assert "field3" in missing

    def test_infer_schema(self, tmp_path):
        """Test schema inference."""
        validator = SchemaValidator(tmp_path)

        data = {
            "name": "test",
            "count": 42,
            "active": True,
            "values": [1, 2, 3],
        }

        schema = validator.infer_schema(data)

        assert schema["type"] == "object"
        assert "properties" in schema
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["count"]["type"] == "integer"
        assert schema["properties"]["active"]["type"] == "boolean"
        assert schema["properties"]["values"]["type"] == "array"


class TestOutputFormatter:
    """Test output formatting."""

    def test_format_single_response(self):
        """Test formatting single agent response."""
        formatter = OutputFormatter()

        response = AgentResponse(
            success=True,
            data={"result": 42},
            agent_name="test-agent",
            execution_time=0.5,
        )

        output = formatter.format_single_response(response, request_id="test-123")

        assert output["success"] is True
        assert output["data"]["result"] == 42
        assert output["_metadata"]["agent"] == "test-agent"
        assert output["_metadata"]["request_id"] == "test-123"

    def test_format_multiple_responses_aggregate(self):
        """Test aggregating multiple responses."""
        formatter = OutputFormatter()

        responses = [
            AgentResponse(
                success=True,
                data={"result": 1},
                agent_name="agent1",
                execution_time=0.1,
            ),
            AgentResponse(
                success=True,
                data={"result": 2},
                agent_name="agent2",
                execution_time=0.2,
            ),
        ]

        output = formatter.format_multiple_responses(
            responses,
            request_id="test-123",
            aggregate=True,
        )

        assert output["success"] is True
        assert "agent1" in output["data"]
        assert "agent2" in output["data"]
        assert output["_metadata"]["count"] == 2
        assert output["_metadata"]["successful"] == 2

    def test_format_error_output(self):
        """Test error output formatting."""
        formatter = OutputFormatter()

        output = formatter.create_error_output(
            error_message="Test error",
            request_id="test-123",
        )

        assert output["success"] is False
        assert output["error"] == "Test error"
        assert output["_metadata"]["request_id"] == "test-123"

    def test_to_json(self):
        """Test JSON conversion."""
        formatter = OutputFormatter(pretty_print=True)

        output = {"test": "value", "number": 42}
        json_str = formatter.to_json(output)

        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["test"] == "value"
        assert parsed["number"] == 42
