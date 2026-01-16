#!/usr/bin/env python3
"""
Interactive Agent Orchestrator Testing Script

This script allows you to test the orchestrator in real-time by:
- Accepting user messages/queries
- Processing them through the orchestrator
- Displaying results in a readable format
- Showing execution metadata (agents used, timing, reasoning)

Commands:
  /help      - Show available commands and example queries
  /examples  - Show example queries you can try
  /stats     - Show orchestrator statistics
  /quit      - Exit the interactive session
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from agent_orchestrator import Orchestrator

# Load environment variables
load_dotenv()

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_banner():
    """Print the interactive session banner."""
    print("\n" + "=" * 70)
    print(f"{Colors.BOLD}{Colors.OKBLUE}Agent Orchestrator - Interactive Testing{Colors.ENDC}")
    print("=" * 70)
    print("\nType your query or use commands:")
    print(f"  {Colors.OKCYAN}/help{Colors.ENDC}     - Show available commands")
    print(f"  {Colors.OKCYAN}/examples{Colors.ENDC} - Show example queries")
    print(f"  {Colors.OKCYAN}/stats{Colors.ENDC}    - Show orchestrator statistics")
    print(f"  {Colors.OKCYAN}/quit{Colors.ENDC}     - Exit the session")
    print("\n" + "=" * 70 + "\n")


def print_help():
    """Print help information."""
    print("\n" + "─" * 70)
    print(f"{Colors.BOLD}Available Commands:{Colors.ENDC}")
    print("─" * 70)
    print(f"\n  {Colors.OKCYAN}/help{Colors.ENDC}")
    print("    Show this help message")
    print(f"\n  {Colors.OKCYAN}/examples{Colors.ENDC}")
    print("    Show example queries you can try")
    print(f"\n  {Colors.OKCYAN}/stats{Colors.ENDC}")
    print("    Show current orchestrator statistics")
    print(f"\n  {Colors.OKCYAN}/quit{Colors.ENDC}")
    print("    Exit the interactive session")
    print("\n" + "─" * 70)
    print(f"\n{Colors.BOLD}Query Format:{Colors.ENDC}")
    print("─" * 70)
    print("\n  You can enter queries in two ways:")
    print("\n  1. Natural language (AI will parse):")
    print("     calculate 15 + 27")
    print("     search for python tutorials")
    print("     find the average of 10, 20, 30")
    print("\n  2. JSON format (for precise control):")
    print('     {"query": "calculate", "operation": "add", "operands": [15, 27]}')
    print('     {"query": "search", "keywords": ["python"], "max_results": 5}')
    print("\n" + "─" * 70 + "\n")


def print_examples():
    """Print example queries."""
    print("\n" + "─" * 70)
    print(f"{Colors.BOLD}Example Queries:{Colors.ENDC}")
    print("─" * 70)

    examples = [
        {
            "category": "Mathematics (Calculator Agent)",
            "queries": [
                "calculate 15 + 27",
                "multiply 8 by 9",
                "divide 100 by 4",
                "find the average of 25, 30, 45",
                '{"query": "calculate", "operation": "add", "operands": [15, 27]}',
            ]
        },
        {
            "category": "Search (Search Agent)",
            "queries": [
                "search for python tutorials",
                "find documents about machine learning",
                '{"query": "search", "keywords": ["AI"], "max_results": 5}',
            ]
        },
        {
            "category": "Data Processing (Data Processor Agent)",
            "queries": [
                "process the data and calculate statistics",
                '{"query": "process data", "data": [{"age": 25}, {"age": 30}], "operation": "aggregate"}',
            ]
        },
        {
            "category": "Multi-Agent Workflows",
            "queries": [
                "search for AI tutorials and calculate their average rating",
                "find documents and process the data",
            ]
        },
    ]

    for i, example_group in enumerate(examples, 1):
        print(f"\n{Colors.OKGREEN}{i}. {example_group['category']}{Colors.ENDC}")
        for query in example_group['queries']:
            print(f"   • {query}")

    print("\n" + "─" * 70 + "\n")


def print_stats(orchestrator: Orchestrator):
    """Print orchestrator statistics."""
    stats = orchestrator.get_stats()

    print("\n" + "─" * 70)
    print(f"{Colors.BOLD}Orchestrator Statistics:{Colors.ENDC}")
    print("─" * 70)

    print(f"\n{Colors.OKGREEN}General:{Colors.ENDC}")
    print(f"  Orchestrator Name: {stats['name']}")
    print(f"  Total Requests: {stats['request_count']}")

    print(f"\n{Colors.OKGREEN}Agents:{Colors.ENDC}")
    agents_info = stats.get('agents', {})
    print(f"  Total Agents: {agents_info.get('total_agents', 0)}")
    print(f"  Capabilities: {', '.join(agents_info.get('capabilities', []))}")

    if agents_info.get('agents'):
        print(f"\n  {Colors.UNDERLINE}Individual Agent Stats:{Colors.ENDC}")
        for agent in agents_info['agents']:
            print(f"\n    • {agent['name']}")
            print(f"      Capabilities: {', '.join(agent.get('capabilities', []))}")
            print(f"      Calls: {agent.get('call_count', 0)}")
            print(f"      Success Rate: {agent.get('success_rate', 0):.1%}")
            if agent.get('avg_execution_time'):
                print(f"      Avg Time: {agent['avg_execution_time']:.3f}s")
            print(f"      Healthy: {'✅' if agent.get('is_healthy') else '❌'}")

    if stats.get('reasoning'):
        print(f"\n{Colors.OKGREEN}Reasoning:{Colors.ENDC}")
        reasoning = stats['reasoning']
        print(f"  Mode: {reasoning.get('mode', 'N/A')}")
        if 'rule_matches' in reasoning:
            print(f"  Rule Matches: {reasoning['rule_matches']}")
        if 'ai_calls' in reasoning:
            print(f"  AI Calls: {reasoning['ai_calls']}")

    print("\n" + "─" * 70 + "\n")


def format_result(result: Dict[str, Any]) -> str:
    """Format orchestrator result for display."""
    output = []

    # Success status
    success = result.get('success', False)
    status_color = Colors.OKGREEN if success else Colors.FAIL
    status_text = "✅ SUCCESS" if success else "❌ FAILED"
    output.append(f"\n{status_color}{Colors.BOLD}{status_text}{Colors.ENDC}")

    # Agent trail
    metadata = result.get('_metadata', {})
    agent_trail = metadata.get('agent_trail', [])
    if agent_trail:
        output.append(f"\n{Colors.OKCYAN}Agents Used:{Colors.ENDC} {' → '.join(agent_trail)}")

    # Execution time
    exec_time = metadata.get('total_execution_time', 0)
    if exec_time:
        output.append(f"{Colors.OKCYAN}Execution Time:{Colors.ENDC} {exec_time:.3f}s")

    # Reasoning information
    reasoning = metadata.get('reasoning', {})
    if reasoning:
        output.append(f"\n{Colors.OKBLUE}Reasoning:{Colors.ENDC}")
        output.append(f"  Method: {reasoning.get('method', 'N/A')}")
        output.append(f"  Confidence: {reasoning.get('confidence', 'N/A')}")
        if reasoning.get('explanation'):
            output.append(f"  Explanation: {reasoning['explanation']}")
        if 'parallel' in reasoning:
            parallel_text = "Yes (parallel)" if reasoning['parallel'] else "No (sequential)"
            output.append(f"  Parallel Execution: {parallel_text}")

    # Result data
    data = result.get('data', {})
    if data:
        output.append(f"\n{Colors.OKGREEN}Result Data:{Colors.ENDC}")

        # Pretty print each agent's output
        for agent_name, agent_data in data.items():
            output.append(f"\n  {Colors.UNDERLINE}{agent_name}:{Colors.ENDC}")

            # Format the data nicely
            if isinstance(agent_data, dict):
                # For calculator results, show simplified format
                if 'result' in agent_data and 'operation' in agent_data:
                    output.append(f"    Result: {agent_data['result']}")
                    output.append(f"    Operation: {agent_data['operation']}")
                    if 'expression' in agent_data:
                        output.append(f"    Expression: {agent_data['expression']}")

                # For search results, show count and top results
                elif 'results' in agent_data and isinstance(agent_data['results'], list):
                    total = agent_data.get('total_count', len(agent_data['results']))
                    output.append(f"    Total Results: {total}")
                    if agent_data['results']:
                        output.append(f"    Top Results:")
                        for i, r in enumerate(agent_data['results'][:3], 1):
                            title = r.get('title', 'Untitled')
                            relevance = r.get('relevance', 0)
                            output.append(f"      {i}. {title} (relevance: {relevance:.2f})")

                # For other dict data, show key info
                else:
                    for key, value in list(agent_data.items())[:5]:  # Limit to 5 keys
                        if isinstance(value, (str, int, float, bool)):
                            output.append(f"    {key}: {value}")
                        elif isinstance(value, list) and len(value) <= 3:
                            output.append(f"    {key}: {value}")
                        else:
                            output.append(f"    {key}: {type(value).__name__}")
            else:
                output.append(f"    {agent_data}")

    # Errors
    errors = result.get('errors', [])
    if errors:
        output.append(f"\n{Colors.WARNING}Errors:{Colors.ENDC}")
        for error in errors:
            agent_name = error.get('agent_name', 'Unknown')
            error_msg = error.get('error', 'Unknown error')
            output.append(f"  • {agent_name}: {error_msg}")

    return '\n'.join(output)


def parse_user_input(user_input: str) -> Dict[str, Any]:
    """
    Parse user input into a request dict.

    Handles both natural language and JSON format.
    """
    user_input = user_input.strip()

    # Try to parse as JSON first
    if user_input.startswith('{'):
        try:
            return json.loads(user_input)
        except json.JSONDecodeError:
            pass

    # Otherwise, treat as natural language query
    request = {"query": user_input}

    # Try to extract common patterns and add parameters
    lower_query = user_input.lower()

    # Math operations
    if any(word in lower_query for word in ['calculate', 'compute', 'add', 'subtract', 'multiply', 'divide', 'average', 'sum']):
        # Try to extract numbers
        import re
        numbers = re.findall(r'\d+(?:\.\d+)?', user_input)
        if numbers:
            operands = [float(n) if '.' in n else int(n) for n in numbers]
            request['operands'] = operands

            # Determine operation
            if 'add' in lower_query or 'sum' in lower_query or '+' in user_input:
                request['operation'] = 'add'
            elif 'subtract' in lower_query or '-' in user_input:
                request['operation'] = 'subtract'
            elif 'multiply' in lower_query or 'times' in lower_query or '*' in user_input or '×' in user_input:
                request['operation'] = 'multiply'
            elif 'divide' in lower_query or '/' in user_input or '÷' in user_input:
                request['operation'] = 'divide'
            elif 'average' in lower_query or 'mean' in lower_query:
                request['operation'] = 'average'

    # Search operations
    if 'search' in lower_query or 'find' in lower_query:
        request['max_results'] = 5

    return request


async def interactive_session(orchestrator: Orchestrator):
    """Run an interactive session with the orchestrator."""
    print_banner()

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print(f"{Colors.WARNING}⚠️  WARNING: ANTHROPIC_API_KEY not set.{Colors.ENDC}")
        print("AI reasoning will be limited. Rule-based routing will be used.")
        print("Set the environment variable in .env file for full AI capabilities.\n")

    request_count = 0

    while True:
        try:
            # Get user input
            user_input = input(f"{Colors.BOLD}You >{Colors.ENDC} ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith('/'):
                command = user_input.lower()

                if command == '/quit' or command == '/exit' or command == '/q':
                    print(f"\n{Colors.OKGREEN}Goodbye!{Colors.ENDC}\n")
                    break

                elif command == '/help' or command == '/h':
                    print_help()
                    continue

                elif command == '/examples' or command == '/ex':
                    print_examples()
                    continue

                elif command == '/stats' or command == '/s':
                    print_stats(orchestrator)
                    continue

                else:
                    print(f"{Colors.WARNING}Unknown command: {user_input}{Colors.ENDC}")
                    print(f"Type {Colors.OKCYAN}/help{Colors.ENDC} for available commands.\n")
                    continue

            # Process the request
            request_count += 1
            print(f"\n{Colors.OKCYAN}[Request #{request_count}]{Colors.ENDC}")
            print(f"Processing: {user_input}")

            # Parse user input
            request = parse_user_input(user_input)

            # Show parsed request if it has additional fields
            if len(request) > 1:
                print(f"{Colors.OKBLUE}Parsed as:{Colors.ENDC} {json.dumps(request, indent=2)}")

            # Process through orchestrator
            start_time = datetime.now()
            result = await orchestrator.process(request)
            end_time = datetime.now()

            # Display result
            print(format_result(result))

            print(f"\n{Colors.OKCYAN}{'─' * 70}{Colors.ENDC}\n")

        except KeyboardInterrupt:
            print(f"\n\n{Colors.WARNING}Interrupted by user.{Colors.ENDC}")
            print(f"{Colors.OKGREEN}Goodbye!{Colors.ENDC}\n")
            break

        except EOFError:
            print(f"\n\n{Colors.OKGREEN}Goodbye!{Colors.ENDC}\n")
            break

        except Exception as e:
            print(f"\n{Colors.FAIL}❌ Error processing request:{Colors.ENDC}")
            print(f"{Colors.FAIL}{str(e)}{Colors.ENDC}")

            # Show traceback in debug mode
            if os.getenv("DEBUG"):
                import traceback
                traceback.print_exc()

            print(f"\n{Colors.OKCYAN}{'─' * 70}{Colors.ENDC}\n")


async def main():
    """Main entry point."""
    orchestrator = None

    try:
        # Initialize orchestrator
        print(f"\n{Colors.OKBLUE}Initializing orchestrator...{Colors.ENDC}")
        orchestrator = Orchestrator(config_path="config/orchestrator.yaml")
        await orchestrator.initialize()

        # Show initialization info
        stats = orchestrator.get_stats()
        agent_count = stats['agents']['total_agents']
        capabilities = stats['agents']['capabilities']

        print(f"{Colors.OKGREEN}✅ Orchestrator initialized successfully!{Colors.ENDC}")
        print(f"   Agents: {agent_count}")
        print(f"   Capabilities: {', '.join(capabilities)}")

        # Run interactive session
        await interactive_session(orchestrator)

    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Interrupted by user.{Colors.ENDC}\n")

    except Exception as e:
        print(f"\n{Colors.FAIL}❌ Error initializing orchestrator:{Colors.ENDC}")
        print(f"{Colors.FAIL}{str(e)}{Colors.ENDC}")

        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        # Cleanup
        if orchestrator:
            print(f"{Colors.OKBLUE}Cleaning up orchestrator...{Colors.ENDC}")
            await orchestrator.cleanup()
            print(f"{Colors.OKGREEN}✅ Cleanup complete.{Colors.ENDC}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.OKGREEN}Goodbye!{Colors.ENDC}\n")
        sys.exit(0)
