#!/usr/bin/env python3
"""
Example usage of the Agent Orchestrator.

This script demonstrates how to use the orchestrator to process requests
through multiple agents with intelligent routing.
"""

import asyncio
import json
import os
import sys
from dotenv import load_dotenv

from agent_orchestrator import Orchestrator

# Load environment variables from .env file
load_dotenv()


async def example_calculation(orchestrator: Orchestrator):
    """Example: Using the orchestrator for calculations."""
    print("=" * 60)
    print("Example 1: Mathematical Calculation")
    print("=" * 60)

    result = await orchestrator.process({
        "query": "calculate the sum of 15 and 27",
        "operation": "add",
        "operands": [15, 27]
    })

    print(f"\nInput: calculate 15 + 27")
    print(f"Success: {result['success']}")
    print(f"Data: {json.dumps(result['data'], indent=2)}")
    print(f"Reasoning: {result.get('_metadata', {}).get('reasoning', {}).get('method')}")


async def example_search(orchestrator: Orchestrator):
    """Example: Using the orchestrator for search."""
    print("\n" + "=" * 60)
    print("Example 2: Document Search")
    print("=" * 60)

    result = await orchestrator.process({
        "query": "search for python programming tutorials",
        "max_results": 3,
    })

    print(f"\nInput: search for python tutorials")
    print(f"Success: {result['success']}")

    if result['success'] and 'search' in result.get('data', {}):
        search_results = result['data']['search']
        print(f"Found {search_results.get('total_count', 0)} results:")
        for r in search_results.get('results', [])[:3]:
            print(f"  - {r['title']} (relevance: {r['relevance']:.2f})")


async def example_data_processing(orchestrator: Orchestrator):
    """Example: Using the orchestrator for data processing."""
    print("\n" + "=" * 60)
    print("Example 3: Data Processing")
    print("=" * 60)

    sample_data = [
        {"name": "Alice", "age": 30, "score": 85},
        {"name": "Bob", "age": 25, "score": 92},
        {"name": "Charlie", "age": 30, "score": 78},
    ]

    result = await orchestrator.process({
        "query": "process and transform the data",
        "data": sample_data,
        "operation": "aggregate",
        "filters": {
            "aggregations": ["count", "avg", "max"]
        }
    })

    print(f"\nInput: {len(sample_data)} records")
    print(f"Success: {result['success']}")
    print(f"Aggregated data: {json.dumps(result.get('data', {}), indent=2)}")


async def example_ai_reasoning(orchestrator: Orchestrator):
    """Example: Demonstrate AI-based reasoning for complex queries."""
    print("\n" + "=" * 60)
    print("Example 4: AI-Based Intelligent Routing")
    print("=" * 60)
    print("\nThis example demonstrates how the orchestrator uses AI to intelligently")
    print("route complex queries that don't match simple rules.")

    # Complex Query 1: Average calculation with AI reasoning
    print("\n" + "-" * 40)
    print("Query 1: Calculate average using AI reasoning")
    print("-" * 40)
    input_1 = {
        "query": "calculate the average of 25, 30, and 45",
        "operation": "average",
        "operands": [25, 30, 45],
    }
    print(f"Input: {json.dumps(input_1, indent=2)}")

    result_1 = await orchestrator.process(input_1)

    print(f"\nOutput:")
    print(f"  Success: {result_1['success']}")
    if result_1['success']:
        print(f"  Data: {json.dumps(result_1.get('data', {}), indent=2)}")

    reasoning_1 = result_1.get('_metadata', {}).get('reasoning', {})
    print(f"\nAI Reasoning:")
    print(f"  Method: {reasoning_1.get('method', 'N/A')}")
    print(f"  Confidence: {reasoning_1.get('confidence', 'N/A')}")
    selected_agents_1 = reasoning_1.get('selected_agents', [])
    print(f"  Selected Agent(s): {', '.join(selected_agents_1) if selected_agents_1 else 'N/A'}")
    print(f"  Explanation: {reasoning_1.get('explanation', 'N/A')}")
    print(f"  Parallel Execution: {reasoning_1.get('parallel', False)}")

    # Complex Query 2: Division with both calculation and search
    print("\n" + "-" * 40)
    print("Query 2: Multi-intent request (calculate + search)")
    print("-" * 40)
    input_2 = {
        "query": "divide 100 by 4 and search for division tutorials",
        "operation": "divide",
        "operands": [100, 4],
    }
    print(f"Input: {json.dumps(input_2, indent=2)}")

    result_2 = await orchestrator.process(input_2)

    print(f"\nOutput:")
    print(f"  Success: {result_2['success']}")
    if result_2['success']:
        print(f"  Data: {json.dumps(result_2.get('data', {}), indent=2)}")

    reasoning_2 = result_2.get('_metadata', {}).get('reasoning', {})
    print(f"\nAI Reasoning:")
    print(f"  Method: {reasoning_2.get('method', 'N/A')}")
    print(f"  Confidence: {reasoning_2.get('confidence', 'N/A')}")
    selected_agents_2 = reasoning_2.get('selected_agents', [])
    print(f"  Selected Agent(s): {', '.join(selected_agents_2) if selected_agents_2 else 'N/A'}")
    print(f"  Explanation: {reasoning_2.get('explanation', 'N/A')}")
    print(f"  Parallel Execution: {reasoning_2.get('parallel', False)}")

    # Complex Query 3: Word problem with calculation
    print("\n" + "-" * 40)
    print("Query 3: Natural language word problem")
    print("-" * 40)
    input_3 = {
        "query": "I have 45 apples to distribute equally among 9 people. How many per person?",
        "operation": "divide",
        "operands": [45, 9],
    }
    print(f"Input: {json.dumps(input_3, indent=2)}")

    result_3 = await orchestrator.process(input_3)

    print(f"\nOutput:")
    print(f"  Success: {result_3['success']}")
    if result_3['success']:
        print(f"  Data: {json.dumps(result_3.get('data', {}), indent=2)}")

    reasoning_3 = result_3.get('_metadata', {}).get('reasoning', {})
    print(f"\nAI Reasoning:")
    print(f"  Method: {reasoning_3.get('method', 'N/A')}")
    print(f"  Confidence: {reasoning_3.get('confidence', 'N/A')}")
    selected_agents_3 = reasoning_3.get('selected_agents', [])
    print(f"  Selected Agent(s): {', '.join(selected_agents_3) if selected_agents_3 else 'N/A'}")
    print(f"  Explanation: {reasoning_3.get('explanation', 'N/A')}")
    print(f"  Parallel Execution: {reasoning_3.get('parallel', False)}")

    print("\n" + "=" * 60)
    print("AI Reasoning Analysis Complete")
    print("=" * 60)
    print("\nKey Observations:")
    print("- Orchestrator uses hybrid reasoning (rule-first, AI-fallback)")
    print("- Selects appropriate agents based on query content and parameters")
    print("- Reasoning method shows whether rules or AI was used")
    print("- Confidence scores indicate certainty of agent selection")
    print("- Supports both simple rule-based and complex AI-based routing")


async def example_stats(orchestrator: Orchestrator):
    """Example: Get orchestrator statistics with detailed request logs."""
    print("\n" + "=" * 60)
    print("Example 5: Orchestrator Statistics")
    print("=" * 60)

    print("\n--- Processing Additional Requests for Stats ---\n")

    # Request 1: Calculate 5 + 3
    print("Request 1: Calculate 5 + 3")
    print("-" * 40)
    input_1 = {"query": "calculate 5 + 3", "operation": "add", "operands": [5, 3]}
    print(f"Input: {json.dumps(input_1, indent=2)}")

    result_1 = await orchestrator.process(input_1)

    print(f"\nOutput:")
    print(f"  Success: {result_1['success']}")
    if result_1['success']:
        print(f"  Result: {result_1['data']['calculator']['result']}")

    reasoning_1 = result_1.get('_metadata', {}).get('reasoning', {})
    print(f"\nReasoning:")
    print(f"  Method: {reasoning_1.get('method', 'N/A')}")
    print(f"  Confidence: {reasoning_1.get('confidence', 'N/A')}")
    selected_agents_1 = reasoning_1.get('selected_agents', [])
    print(f"  Selected Agent(s): {', '.join(selected_agents_1) if selected_agents_1 else 'N/A'}")
    print(f"  Explanation: {reasoning_1.get('explanation', 'N/A')}")

    # Request 2: Search for AI
    print("\n" + "-" * 40)
    print("Request 2: Search for AI")
    print("-" * 40)
    input_2 = {"query": "search for AI", "max_results": 5}
    print(f"Input: {json.dumps(input_2, indent=2)}")

    result_2 = await orchestrator.process(input_2)

    print(f"\nOutput:")
    print(f"  Success: {result_2['success']}")
    if result_2['success'] and 'search' in result_2.get('data', {}):
        search_data = result_2['data']['search']
        print(f"  Results Found: {search_data.get('total_count', 0)}")
        print(f"  Top Result: {search_data.get('results', [{}])[0].get('title', 'N/A')}")

    reasoning_2 = result_2.get('_metadata', {}).get('reasoning', {})
    print(f"\nReasoning:")
    print(f"  Method: {reasoning_2.get('method', 'N/A')}")
    print(f"  Confidence: {reasoning_2.get('confidence', 'N/A')}")
    selected_agents_2 = reasoning_2.get('selected_agents', [])
    print(f"  Selected Agent(s): {', '.join(selected_agents_2) if selected_agents_2 else 'N/A'}")
    print(f"  Explanation: {reasoning_2.get('explanation', 'N/A')}")

    # Get overall stats
    print("\n" + "=" * 60)
    print("Overall Orchestrator Statistics")
    print("=" * 60)
    stats = orchestrator.get_stats()

    print(f"\nOrchestrator: {stats['name']}")
    print(f"Total Requests Processed: {stats['request_count']}")
    print(f"Registered Agents: {stats['agents']['total_agents']}")
    print(f"Available Capabilities: {', '.join(stats['agents']['capabilities'])}")

    # Show reasoning stats if available
    if stats.get('reasoning'):
        print(f"\nReasoning Statistics:")
        reasoning_stats = stats['reasoning']
        if 'rule_matches' in reasoning_stats:
            print(f"  Rule Matches: {reasoning_stats['rule_matches']}")
        if 'ai_calls' in reasoning_stats:
            print(f"  AI Calls: {reasoning_stats['ai_calls']}")


async def main():
    """Run all examples."""
    print("Agent Orchestrator - Example Usage")
    print("=" * 60)

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\nWARNING: ANTHROPIC_API_KEY not set.")
        print("AI reasoning will not be available.")
        print("Set the environment variable or update .env file.")
        print("\nContinuing with rule-based reasoning only...")
        print()

    # Initialize orchestrator once
    orchestrator = None

    try:
        # Initialize orchestrator
        print("\nInitializing orchestrator...")
        orchestrator = Orchestrator(config_path="config/orchestrator.yaml")
        await orchestrator.initialize()

        # Get agent count from stats
        stats = orchestrator.get_stats()
        agent_count = stats['agents']['total_agents']
        print(f"Orchestrator initialized with {agent_count} agents\n")

        # Run examples with shared orchestrator instance
        await example_calculation(orchestrator)
        await example_search(orchestrator)
        await example_data_processing(orchestrator)
        await example_ai_reasoning(orchestrator)
        await example_stats(orchestrator)

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        # Cleanup orchestrator
        if orchestrator:
            print("\nCleaning up orchestrator...")
            await orchestrator.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
