
from fastmcp import FastMCP
from typing import List

# Create an MCP server
mcp = FastMCP("Math Server")

@mcp.tool()
def calculate(operation: str, operands: List[float]) -> float:
    """
    Perform mathematical calculations.
    
    Args:
        operation: Operation to perform (add, subtract, multiply, divide)
        operands: List of numbers to operate on
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

    if operation == "add":
        return sum(operands)
    elif operation == "subtract":
        if len(operands) < 2:
            raise ValueError("Subtract requires at least 2 operands")
        return operands[0] - sum(operands[1:])
    elif operation == "multiply":
        result = 1.0
        for num in operands:
            result *= num
        return result
    elif operation == "divide":
        if len(operands) < 2:
            raise ValueError("Divide requires at least 2 operands")
        result = operands[0]
        for num in operands[1:]:
            if num == 0:
                raise ValueError("Division by zero")
            result /= num
        return result
    
    raise ValueError(f"Unknown operation: {operation}")

if __name__ == "__main__":
    mcp.run()

if __name__ == "__main__":
    mcp.run(transport="stdio")
