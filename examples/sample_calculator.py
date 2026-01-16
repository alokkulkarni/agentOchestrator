"""
Sample calculator tool for direct agent demonstration.

This module provides mathematical calculation functions that can be
called directly as agents without MCP protocol.
"""

from typing import Dict, List, Union


def calculate(operation: str, operands: List[float]) -> Dict[str, Union[float, str, List[float]]]:
    """
    Perform mathematical calculations.

    Args:
        operation: Operation to perform (add, subtract, multiply, divide, power, sqrt)
        operands: List of numbers to operate on

    Returns:
        Dictionary with result, operation, and operands

    Raises:
        ValueError: If operation is invalid or operands are insufficient
    """
    if not operands:
        raise ValueError("At least one operand required")

    operation = operation.lower()

    # Normalize operation names
    if operation in ["addition", "sum", "plus"]:
        operation = "add"
    elif operation in ["subtraction", "minus", "difference"]:
        operation = "subtract"
    elif operation in ["multiplication", "times", "product"]:
        operation = "multiply"
    elif operation in ["division", "div", "divided"]:
        operation = "divide"
    elif operation in ["average", "avg", "mean"]:
        # Calculate average
        result = sum(operands) / len(operands)
        return {
            "result": result,
            "operation": "average",
            "operands": operands,
            "expression": f"avg({', '.join(str(x) for x in operands)})",
        }

    if operation == "add":
        result = sum(operands)
    elif operation == "subtract":
        if len(operands) < 2:
            raise ValueError("Subtract requires at least 2 operands")
        result = operands[0] - sum(operands[1:])
    elif operation == "multiply":
        result = 1.0
        for num in operands:
            result *= num
    elif operation == "divide":
        if len(operands) < 2:
            raise ValueError("Divide requires at least 2 operands")
        result = operands[0]
        for num in operands[1:]:
            if num == 0:
                raise ValueError("Division by zero")
            result /= num
    elif operation == "power":
        if len(operands) != 2:
            raise ValueError("Power requires exactly 2 operands (base, exponent)")
        result = operands[0] ** operands[1]
    elif operation == "sqrt":
        if len(operands) != 1:
            raise ValueError("Sqrt requires exactly 1 operand")
        if operands[0] < 0:
            raise ValueError("Cannot take square root of negative number")
        result = operands[0] ** 0.5
    else:
        raise ValueError(f"Unknown operation: {operation}")

    return {
        "result": result,
        "operation": operation,
        "operands": operands,
        "expression": _format_expression(operation, operands),
    }


def _format_expression(operation: str, operands: List[float]) -> str:
    """Format calculation as a readable expression."""
    if operation == "add":
        return " + ".join(str(x) for x in operands)
    elif operation == "subtract":
        return " - ".join(str(x) for x in operands)
    elif operation == "multiply":
        return " * ".join(str(x) for x in operands)
    elif operation == "divide":
        return " / ".join(str(x) for x in operands)
    elif operation == "power":
        return f"{operands[0]} ^ {operands[1]}"
    elif operation == "sqrt":
        return f"√{operands[0]}"
    else:
        return str(operands)


# Example usage
if __name__ == "__main__":
    # Test calculations
    print(calculate("add", [1, 2, 3, 4]))
    print(calculate("multiply", [2, 3, 4]))
    print(calculate("power", [2, 8]))
    print(calculate("sqrt", [16]))
