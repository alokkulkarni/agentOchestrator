"""
Sample data processor tool for direct agent demonstration.

This module provides data transformation and processing functions
that can be called directly as agents without MCP protocol.
"""

import json
from typing import Any, Dict, List, Union


def process_data(
    data: Union[List[Dict], Dict],
    operation: str = "transform",
    filters: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Process and transform structured data.

    Args:
        data: Input data (list of dicts or single dict)
        operation: Operation to perform (transform, filter, aggregate, sort)
        filters: Optional filters to apply

    Returns:
        Processed data with metadata
    """
    filters = filters or {}
    operation = operation.lower()

    # Ensure data is a list
    data_list = data if isinstance(data, list) else [data]

    if operation == "transform":
        result = _transform_data(data_list, filters)
    elif operation == "filter":
        result = _filter_data(data_list, filters)
    elif operation == "aggregate":
        result = _aggregate_data(data_list, filters)
    elif operation == "sort":
        result = _sort_data(data_list, filters)
    else:
        raise ValueError(f"Unknown operation: {operation}")

    return {
        "operation": operation,
        "input_count": len(data_list),
        "output_count": len(result) if isinstance(result, list) else 1,
        "result": result,
        "filters_applied": filters,
    }


def _transform_data(data: List[Dict], filters: Dict[str, Any]) -> List[Dict]:
    """Transform data by selecting or renaming fields."""
    select_fields = filters.get("select", None)
    rename_fields = filters.get("rename", {})

    transformed = []

    for item in data:
        new_item = {}

        # Select specific fields if specified
        if select_fields:
            for field in select_fields:
                if field in item:
                    new_item[field] = item[field]
        else:
            new_item = item.copy()

        # Rename fields if specified
        for old_name, new_name in rename_fields.items():
            if old_name in new_item:
                new_item[new_name] = new_item.pop(old_name)

        transformed.append(new_item)

    return transformed


def _filter_data(data: List[Dict], filters: Dict[str, Any]) -> List[Dict]:
    """Filter data based on conditions."""
    conditions = filters.get("conditions", {})

    filtered = []

    for item in data:
        match = True

        for field, expected_value in conditions.items():
            if field not in item:
                match = False
                break

            # Simple equality check (can be extended)
            if item[field] != expected_value:
                match = False
                break

        if match:
            filtered.append(item)

    return filtered


def _aggregate_data(data: List[Dict], filters: Dict[str, Any]) -> Dict[str, Any]:
    """Aggregate data by computing statistics."""
    group_by = filters.get("group_by", None)
    aggregations = filters.get("aggregations", ["count"])

    if group_by:
        # Group by field
        groups = {}
        for item in data:
            key = item.get(group_by, "unknown")
            if key not in groups:
                groups[key] = []
            groups[key].append(item)

        result = {}
        for key, items in groups.items():
            result[key] = _compute_aggregations(items, aggregations)

        return result
    else:
        # Aggregate all data
        return _compute_aggregations(data, aggregations)


def _compute_aggregations(data: List[Dict], aggregations: List[str]) -> Dict[str, Any]:
    """Compute aggregation statistics."""
    result = {}

    if "count" in aggregations:
        result["count"] = len(data)

    # Extract numeric fields for other aggregations
    numeric_fields = {}
    if data:
        for field, value in data[0].items():
            if isinstance(value, (int, float)):
                numeric_fields[field] = []

        for item in data:
            for field in numeric_fields:
                if field in item and isinstance(item[field], (int, float)):
                    numeric_fields[field].append(item[field])

    # Compute other aggregations
    for agg in aggregations:
        if agg == "count":
            continue

        if agg == "sum":
            for field, values in numeric_fields.items():
                result[f"{field}_sum"] = sum(values)
        elif agg == "avg":
            for field, values in numeric_fields.items():
                result[f"{field}_avg"] = sum(values) / len(values) if values else 0
        elif agg == "min":
            for field, values in numeric_fields.items():
                result[f"{field}_min"] = min(values) if values else None
        elif agg == "max":
            for field, values in numeric_fields.items():
                result[f"{field}_max"] = max(values) if values else None

    return result


def _sort_data(data: List[Dict], filters: Dict[str, Any]) -> List[Dict]:
    """Sort data by specified field."""
    sort_by = filters.get("sort_by", None)
    reverse = filters.get("reverse", False)

    if not sort_by:
        return data

    # Sort by field
    try:
        sorted_data = sorted(
            data,
            key=lambda x: x.get(sort_by, ""),
            reverse=reverse
        )
        return sorted_data
    except Exception:
        # If sorting fails, return original data
        return data


# Example usage
if __name__ == "__main__":
    sample_data = [
        {"name": "Alice", "age": 30, "score": 85},
        {"name": "Bob", "age": 25, "score": 92},
        {"name": "Charlie", "age": 30, "score": 78},
    ]

    # Test transform
    print("Transform:")
    print(process_data(sample_data, "transform", {"select": ["name", "score"]}))

    # Test filter
    print("\nFilter:")
    print(process_data(sample_data, "filter", {"conditions": {"age": 30}}))

    # Test aggregate
    print("\nAggregate:")
    print(process_data(sample_data, "aggregate", {"aggregations": ["count", "avg", "max"]}))

    # Test sort
    print("\nSort:")
    print(process_data(sample_data, "sort", {"sort_by": "score", "reverse": True}))
