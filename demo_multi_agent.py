#!/usr/bin/env python3
"""
Demonstration: Multi-Agent Request Distribution & Consolidation

This script demonstrates how the orchestrator can:
1. Analyze a user request
2. Determine multiple agents are needed
3. Execute them (sequentially or in parallel)
4. Consolidate the outputs
"""

import json


def demonstrate_multi_agent_concepts():
    """Demonstrate multi-agent orchestration concepts."""
    print("=" * 70)
    print("MULTI-AGENT REQUEST DISTRIBUTION & CONSOLIDATION")
    print("=" * 70)

    # Example 1: Sequential Multi-Agent
    print("\n" + "─" * 70)
    print("EXAMPLE 1: Sequential Multi-Agent Workflow")
    print("─" * 70)

    print("\n📥 USER REQUEST:")
    print('   "Find documents about AI and calculate their sentiment scores"')

    print("\n🧠 AI REASONER ANALYSIS:")
    print("   • Detected: 'find documents' → needs search capability")
    print("   • Detected: 'calculate sentiment' → needs data processing")
    print("   • Dependency: Must search first, then process results")
    print("   • Mode: SEQUENTIAL")

    reasoning_result = {
        "agents": ["search", "data_processor"],
        "reasoning": "First search for documents, then analyze sentiment of results",
        "confidence": 0.88,
        "parallel": False,
        "parameters": {
            "search": {"query": "AI documents", "max_results": 10},
            "data_processor": {"operation": "sentiment_analysis"}
        }
    }

    print("\n📋 REASONING RESULT:")
    print(f"   Selected agents: {reasoning_result['agents']}")
    print(f"   Confidence: {reasoning_result['confidence']}")
    print(f"   Execution mode: {'Parallel' if reasoning_result['parallel'] else 'Sequential'}")
    print(f"   Reasoning: {reasoning_result['reasoning']}")

    print("\n⚙️  EXECUTION:")
    print("   Step 1: Executing 'search' agent...")
    search_output = {
        "results": [
            {"title": "AI Research Paper 1", "content": "...positive content..."},
            {"title": "AI Research Paper 2", "content": "...negative content..."},
            {"title": "AI Research Paper 3", "content": "...positive content..."}
        ],
        "total_count": 3
    }
    print(f"   ✅ search completed in 0.42s")
    print(f"      Found {search_output['total_count']} documents")

    print("\n   Step 2: Executing 'data_processor' agent...")
    print("   (Using results from search as input)")
    processor_output = {
        "sentiment_scores": [0.8, -0.3, 0.7],
        "average_sentiment": 0.4,
        "analysis": "Overall positive sentiment"
    }
    print(f"   ✅ data_processor completed in 1.23s")
    print(f"      Calculated sentiment scores: {processor_output['sentiment_scores']}")

    print("\n📦 CONSOLIDATED OUTPUT:")
    consolidated = {
        "success": True,
        "data": {
            "search": search_output,
            "data_processor": processor_output
        },
        "_metadata": {
            "count": 2,
            "successful": 2,
            "failed": 0,
            "agent_trail": ["search", "data_processor"],
            "total_execution_time": 1.65,
            "reasoning": reasoning_result
        }
    }
    print(json.dumps(consolidated, indent=2))

    # Example 2: Parallel Multi-Agent
    print("\n" + "─" * 70)
    print("EXAMPLE 2: Parallel Multi-Agent Workflow")
    print("─" * 70)

    print("\n📥 USER REQUEST:")
    print('   "Get the weather in Tokyo and calculate 15 + 27"')

    print("\n🧠 AI REASONER ANALYSIS:")
    print("   • Detected: 'get weather' → needs weather capability")
    print("   • Detected: 'calculate' → needs math capability")
    print("   • Dependency: None! Independent operations")
    print("   • Mode: PARALLEL")

    reasoning_result = {
        "agents": ["weather", "calculator"],
        "reasoning": "Independent operations can run simultaneously",
        "confidence": 0.92,
        "parallel": True,
        "parameters": {
            "weather": {"city": "Tokyo", "units": "celsius"},
            "calculator": {"operation": "add", "operands": [15, 27]}
        }
    }

    print("\n📋 REASONING RESULT:")
    print(f"   Selected agents: {reasoning_result['agents']}")
    print(f"   Confidence: {reasoning_result['confidence']}")
    print(f"   Execution mode: {'Parallel' if reasoning_result['parallel'] else 'Sequential'}")
    print(f"   Reasoning: {reasoning_result['reasoning']}")

    print("\n⚙️  EXECUTION (Parallel):")
    print("   ┌─ Agent 1: 'weather' starting...")
    print("   └─ Agent 2: 'calculator' starting...")
    print("   (Both agents running simultaneously)")

    weather_output = {
        "city": "Tokyo",
        "temperature": 20,
        "condition": "Rainy",
        "humidity": 80
    }
    calculator_output = {
        "result": 42,
        "operation": "add",
        "operands": [15, 27],
        "expression": "15 + 27"
    }

    print(f"\n   ✅ weather completed in 0.85s")
    print(f"      Tokyo: {weather_output['temperature']}°C, {weather_output['condition']}")
    print(f"\n   ✅ calculator completed in 0.12s")
    print(f"      Result: {calculator_output['result']}")

    print("\n   Total time: 0.85s (not 0.97s!)")
    print("   Speedup: ~14% faster with parallel execution")

    print("\n📦 CONSOLIDATED OUTPUT:")
    consolidated = {
        "success": True,
        "data": {
            "weather": weather_output,
            "calculator": calculator_output
        },
        "_metadata": {
            "count": 2,
            "successful": 2,
            "failed": 0,
            "agent_trail": ["weather", "calculator"],
            "total_execution_time": 0.85,
            "max_execution_time": 0.85,
            "parallel": True,
            "reasoning": reasoning_result
        }
    }
    print(json.dumps(consolidated, indent=2))

    # Example 3: Complex Multi-Step
    print("\n" + "─" * 70)
    print("EXAMPLE 3: Complex Multi-Step Workflow (3 Agents)")
    print("─" * 70)

    print("\n📥 USER REQUEST:")
    print('   "Search tutorials, filter by rating > 4.5, and calculate average"')

    print("\n🧠 AI REASONER ANALYSIS:")
    print("   • Step 1: 'search' → search agent")
    print("   • Step 2: 'filter by rating' → data_processor agent")
    print("   • Step 3: 'calculate average' → calculator agent")
    print("   • Mode: SEQUENTIAL (each step depends on previous)")

    reasoning_result = {
        "agents": ["search", "data_processor", "calculator"],
        "reasoning": "Multi-step workflow: search → filter → calculate",
        "confidence": 0.83,
        "parallel": False
    }

    print("\n📋 REASONING RESULT:")
    print(f"   Selected agents: {reasoning_result['agents']}")
    print(f"   Total steps: {len(reasoning_result['agents'])}")
    print(f"   Execution: Sequential (step-by-step)")

    print("\n⚙️  EXECUTION:")
    print("   Step 1/3: search")
    print("   ✅ Found 3 tutorials")

    print("\n   Step 2/3: data_processor (filter)")
    print("   ✅ Filtered to 2 tutorials with rating > 4.5")

    print("\n   Step 3/3: calculator (average)")
    print("   ✅ Calculated average: 4.75")

    print("\n📦 CONSOLIDATED OUTPUT:")
    consolidated = {
        "success": True,
        "data": {
            "search": {
                "results": [
                    {"title": "Tutorial A", "rating": 4.7},
                    {"title": "Tutorial B", "rating": 4.2},
                    {"title": "Tutorial C", "rating": 4.8}
                ],
                "total_count": 3
            },
            "data_processor": {
                "filtered_results": [
                    {"title": "Tutorial A", "rating": 4.7},
                    {"title": "Tutorial C", "rating": 4.8}
                ],
                "count": 2
            },
            "calculator": {
                "result": 4.75,
                "operation": "average"
            }
        },
        "_metadata": {
            "count": 3,
            "successful": 3,
            "agent_trail": ["search", "data_processor", "calculator"],
            "total_execution_time": 2.34
        }
    }
    print(json.dumps(consolidated, indent=2))

    # Summary
    print("\n" + "=" * 70)
    print("KEY CAPABILITIES")
    print("=" * 70)
    print("""
✅ MULTI-AGENT SELECTION
   • AI reasoner can select 1 to N agents
   • Analyzes request to determine requirements
   • Maps requirements to agent capabilities

✅ EXECUTION STRATEGIES
   • Sequential: One after another (when dependent)
   • Parallel: Simultaneously (when independent)
   • Mixed: Combination of both

✅ OUTPUT CONSOLIDATION
   • Merges all agent outputs under agent names
   • Provides unified response structure
   • Tracks execution metadata:
     - Which agents ran (agent_trail)
     - Success/failure counts
     - Execution times
     - Reasoning information

✅ PERFORMANCE OPTIMIZATION
   • Parallel execution for independent agents
   • Sequential for dependent workflows
   • Automatic speedup with parallel mode

✅ ERROR HANDLING
   • Tracks partial successes
   • Graceful degradation
   • Detailed error information per agent
    """)

    print("=" * 70)
    print("ACCESSING CONSOLIDATED RESULTS")
    print("=" * 70)
    print("""
# Access individual agent outputs:
result = await orchestrator.process(request)

search_results = result['data']['search']
processed = result['data']['data_processor']
calculation = result['data']['calculator']

# Access metadata:
agents_used = result['_metadata']['agent_trail']
total_time = result['_metadata']['total_execution_time']
success_count = result['_metadata']['successful']

# Check if parallel execution was used:
was_parallel = result['_metadata']['reasoning']['parallel']
    """)

    print("=" * 70)


if __name__ == "__main__":
    demonstrate_multi_agent_concepts()
