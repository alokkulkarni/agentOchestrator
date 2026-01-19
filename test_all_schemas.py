#!/usr/bin/env python3
"""
Test all validation schemas with sample data.

This script validates that all JSON schemas are properly formatted
and can successfully validate their respective output formats.
"""

import json
from pathlib import Path

try:
    from jsonschema import validate, ValidationError
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    print("⚠️  jsonschema not installed. Install with: pip install jsonschema")
    print("Falling back to basic JSON parsing validation only.\n")

# Test data for each schema
TEST_DATA = {
    "calculation_output.json": {
        "result": 42,
        "operation": "add",
        "operands": [15, 27],
        "expression": "15 + 27",
        "metadata": {
            "precision": 2,
            "timestamp": "2026-01-18T15:30:00Z"
        }
    },
    "search_output.json": {
        "query": "Python tutorial",
        "results": [
            {
                "id": "doc_001",
                "title": "Python Tutorial",
                "content": "Learn Python...",
                "relevance": 0.95,
                "metadata": {"source": "docs"}
            }
        ],
        "total_count": 1,
        "page": 1,
        "has_more": False
    },
    "tavily_search_output.json": {
        "success": True,
        "query": "AI news",
        "results": [
            {
                "title": "Latest AI Developments",
                "url": "https://example.com/ai-news",
                "content": "AI continues to advance...",
                "score": 0.92
            }
        ],
        "answer": "Recent AI developments include...",
        "total_results": 1,
        "search_depth": "basic",
        "timestamp": "2026-01-18T15:30:00Z",
        "metadata": {
            "api": "tavily",
            "version": "1.0"
        }
    },
    "data_processor_output.json": {
        "operation": "aggregate",
        "input_count": 8,
        "output_count": 1,
        "result": {
            "count": 8,
            "salary_avg": 79750,
            "salary_sum": 638000
        },
        "filters_applied": {
            "aggregations": ["count", "avg", "sum"]
        }
    },
    "weather_output.json": {
        "city": "London",
        "temperature": 60,
        "condition": "Cloudy",
        "humidity": 75,
        "unit": "fahrenheit",
        "timestamp": "2026-01-18T15:30:00Z"
    }
}

def test_schemas():
    """Test all schemas with sample data."""
    print("=" * 70)
    print("VALIDATION SCHEMA TESTS")
    print("=" * 70)

    schemas_dir = Path("config/schemas")

    if not schemas_dir.exists():
        print(f"\n❌ Schemas directory not found: {schemas_dir}")
        return

    print(f"\nSchemas directory: {schemas_dir}")
    print(f"Testing {len(TEST_DATA)} schemas\n")

    passed = 0
    failed = 0

    for schema_file, test_data in TEST_DATA.items():
        schema_path = schemas_dir / schema_file

        if not schema_path.exists():
            print(f"❌ {schema_file}: FILE NOT FOUND")
            failed += 1
            continue

        # Load schema
        try:
            with open(schema_path) as f:
                schema = json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ {schema_file}: INVALID JSON")
            print(f"   Error: {e}")
            failed += 1
            continue

        # Validate if jsonschema is available
        if HAS_JSONSCHEMA:
            try:
                validate(instance=test_data, schema=schema)
                print(f"✅ {schema_file}: VALID")
                passed += 1
            except ValidationError as e:
                print(f"❌ {schema_file}: VALIDATION FAILED")
                print(f"   Error: {e.message}")
                print(f"   Path: {' -> '.join(str(p) for p in e.path)}")
                failed += 1
        else:
            # Basic check: schema loads and has required fields
            if "$schema" in schema and "type" in schema:
                print(f"✅ {schema_file}: SCHEMA LOADS (jsonschema validation skipped)")
                passed += 1
            else:
                print(f"❌ {schema_file}: MISSING REQUIRED FIELDS")
                failed += 1

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"\nTotal: {passed + failed} schemas")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")

    if failed == 0:
        print("\n🎉 All schemas validated successfully!")
    else:
        print(f"\n⚠️  {failed} schema(s) failed validation")

    return failed == 0


if __name__ == "__main__":
    import sys

    success = test_schemas()

    if not HAS_JSONSCHEMA:
        print("\n" + "=" * 70)
        print("RECOMMENDATION")
        print("=" * 70)
        print("\nInstall jsonschema for full validation:")
        print("  pip install jsonschema")
        print("\nOr add to requirements.txt:")
        print("  echo 'jsonschema>=4.23.0' >> requirements.txt")
        print("  pip install -r requirements.txt")

    sys.exit(0 if success else 1)
