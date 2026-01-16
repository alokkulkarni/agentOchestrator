#!/usr/bin/env python3
"""
Demonstration: How the Orchestrator Stores and Selects Agents

This script demonstrates:
1. How agents are registered in the registry with their characteristics
2. How the registry indexes agents by capability
3. How the reasoning engine selects the best agent
"""

import asyncio
import json


async def demonstrate_registry():
    """Demonstrate agent registry functionality."""
    from agent_orchestrator.agents import AgentRegistry, DirectAgent
    from agent_orchestrator.config.models import DirectToolConfig

    print("=" * 70)
    print("DEMONSTRATION: Agent Registry & Selection")
    print("=" * 70)

    # Create registry
    registry = AgentRegistry()
    print("\n1. Created empty registry")
    print(f"   Agents: {registry.count()}")

    # Create sample agents
    calculator_config = DirectToolConfig(
        module="examples.sample_calculator",
        function="calculate",
        is_async=False
    )

    calculator = DirectAgent(
        name="calculator",
        capabilities=["math", "calculation", "arithmetic"],
        tool_config=calculator_config,
        metadata={
            "description": "Safe mathematical calculator",
            "version": "1.0.0"
        }
    )

    search_config = DirectToolConfig(
        module="examples.sample_search",
        function="search_documents",
        is_async=True
    )

    search = DirectAgent(
        name="search",
        capabilities=["search", "retrieval", "query"],
        tool_config=search_config,
        metadata={
            "description": "Document search engine",
            "version": "1.0.0"
        }
    )

    data_config = DirectToolConfig(
        module="examples.sample_data_processor",
        function="process_data",
        is_async=False
    )

    data_processor = DirectAgent(
        name="data_processor",
        capabilities=["data", "transform", "json"],
        tool_config=data_config,
        metadata={
            "description": "Data processing and transformation",
            "version": "1.0.0"
        }
    )

    print("\n2. Registering agents with their characteristics...")

    # Register agents
    await registry.register(calculator, initialize=True)
    print(f"   ✅ Registered: calculator")
    print(f"      Capabilities: {calculator.capabilities}")
    print(f"      Description: {calculator.metadata['description']}")

    await registry.register(search, initialize=True)
    print(f"   ✅ Registered: search")
    print(f"      Capabilities: {search.capabilities}")
    print(f"      Description: {search.metadata['description']}")

    await registry.register(data_processor, initialize=True)
    print(f"   ✅ Registered: data_processor")
    print(f"      Capabilities: {data_processor.capabilities}")
    print(f"      Description: {data_processor.metadata['description']}")

    print(f"\n   Total agents registered: {registry.count()}")

    # Show registry stats
    print("\n3. Registry Statistics:")
    stats = registry.get_stats()
    print(f"   Total agents: {stats['total_agents']}")
    print(f"   All capabilities: {', '.join(stats['capabilities'])}")

    # Demonstrate capability lookup
    print("\n4. Finding Agents by Capability:")

    print("\n   Query: Who can do 'math'?")
    math_agents = registry.get_by_capability("math")
    for agent in math_agents:
        print(f"   ✅ Found: {agent.name}")

    print("\n   Query: Who can do 'search'?")
    search_agents = registry.get_by_capability("search")
    for agent in search_agents:
        print(f"   ✅ Found: {agent.name}")

    print("\n   Query: Who can do 'data' processing?")
    data_agents = registry.get_by_capability("data")
    for agent in data_agents:
        print(f"   ✅ Found: {agent.name}")

    # Show all agents
    print("\n5. All Available Agents:")
    all_agents = registry.get_all()
    for agent in all_agents:
        print(f"   - {agent.name}: {', '.join(agent.capabilities)}")

    # Cleanup
    await registry.cleanup_all()
    print("\n6. Registry cleaned up")

    print("\n" + "=" * 70)


async def demonstrate_agent_selection():
    """Demonstrate how reasoning engine selects agents."""
    print("\n" + "=" * 70)
    print("DEMONSTRATION: Intelligent Agent Selection")
    print("=" * 70)

    from agent_orchestrator.reasoning.rule_engine import RuleEngine
    from agent_orchestrator.config.models import RulesConfig, RoutingRule, RuleCondition

    # Create sample rules
    rules = [
        RoutingRule(
            name="calculation_rule",
            priority=100,
            conditions=[
                RuleCondition(
                    type="keyword",
                    field="query",
                    value=["calculate", "compute", "add", "subtract", "multiply", "divide"]
                ),
                RuleCondition(
                    type="field_exists",
                    field="operation"
                )
            ],
            actions=[{
                "type": "route",
                "target_agents": ["calculator"],
                "confidence": 0.9
            }]
        ),
        RoutingRule(
            name="search_rule",
            priority=90,
            conditions=[
                RuleCondition(
                    type="keyword",
                    field="query",
                    value=["search", "find", "look for", "query"]
                )
            ],
            actions=[{
                "type": "route",
                "target_agents": ["search"],
                "confidence": 0.85
            }]
        ),
        RoutingRule(
            name="data_processing_rule",
            priority=85,
            conditions=[
                RuleCondition(
                    type="keyword",
                    field="query",
                    value=["process", "transform", "aggregate", "filter"]
                ),
                RuleCondition(
                    type="field_exists",
                    field="data"
                )
            ],
            actions=[{
                "type": "route",
                "target_agents": ["data_processor"],
                "confidence": 0.88
            }]
        )
    ]

    rules_config = RulesConfig(rules=rules)
    rule_engine = RuleEngine(rules_config)

    print(f"\n1. Loaded {len(rules)} routing rules")

    # Test different requests
    test_requests = [
        {
            "query": "calculate the sum of 15 and 27",
            "operation": "add",
            "operands": [15, 27]
        },
        {
            "query": "search for python programming tutorials",
            "max_results": 5
        },
        {
            "query": "process and transform the user data",
            "data": [{"name": "Alice", "score": 95}],
            "operation": "aggregate"
        },
        {
            "query": "What's the weather like?"  # No rule matches
        }
    ]

    print("\n2. Testing Agent Selection:\n")

    for i, request in enumerate(test_requests, 1):
        print(f"   Request {i}:")
        print(f"   Query: \"{request['query']}\"")

        # Evaluate with rule engine
        matches = rule_engine.evaluate(request)

        if matches:
            best_match = matches[0]
            print(f"   ✅ MATCHED: {best_match.rule_name}")
            print(f"   Selected Agent: {', '.join(best_match.target_agents)}")
            print(f"   Confidence: {best_match.confidence:.2f}")
            print(f"   Reasoning: {', '.join(best_match.matched_conditions)}")
        else:
            print(f"   ❌ NO RULE MATCH")
            print(f"   → Would fallback to AI reasoning")

        print()

    print("=" * 70)


async def demonstrate_ai_context():
    """Show what information AI reasoner receives about agents."""
    print("\n" + "=" * 70)
    print("DEMONSTRATION: AI Reasoner Agent Context")
    print("=" * 70)

    from agent_orchestrator.agents import AgentRegistry, DirectAgent
    from agent_orchestrator.config.models import DirectToolConfig

    # Create registry with sample agents
    registry = AgentRegistry()

    calculator_config = DirectToolConfig(
        module="examples.sample_calculator",
        function="calculate",
        is_async=False
    )

    calculator = DirectAgent(
        name="calculator",
        capabilities=["math", "calculation", "arithmetic"],
        tool_config=calculator_config,
        metadata={
            "description": "Safe mathematical calculator with input validation"
        }
    )

    search_config = DirectToolConfig(
        module="examples.sample_search",
        function="search_documents",
        is_async=True
    )

    search = DirectAgent(
        name="search",
        capabilities=["search", "retrieval", "query", "information"],
        tool_config=search_config,
        metadata={
            "description": "Document search with safe search enabled"
        }
    )

    await registry.register(calculator, initialize=True)
    await registry.register(search, initialize=True)

    print("\n1. Agents Registered in Registry\n")

    # Simulate what AI reasoner sees
    print("2. Agent Context Sent to AI Reasoner:\n")
    print("   " + "-" * 66)

    available_agents = registry.get_all()
    for agent in available_agents:
        stats = agent.get_stats()
        print(f"   - **{agent.name}**:")
        print(f"       Capabilities: {', '.join(agent.capabilities)}")
        if agent.metadata.get("description"):
            print(f"       Description: {agent.metadata['description']}")
        print(f"       Health: {'✅ Healthy' if stats['is_healthy'] else '❌ Unhealthy'}")
        print(f"       Performance: {stats['call_count']} calls, "
              f"{stats['success_rate']*100:.1f}% success rate")
        print()

    print("   " + "-" * 66)

    print("\n3. AI Analyzes This Information:\n")
    print("   For request: \"calculate 2 + 2\"")
    print("   AI reasoning:")
    print("   - Query contains 'calculate' → mathematical operation")
    print("   - 'calculator' agent has 'math' and 'calculation' capabilities")
    print("   - 'calculator' agent is healthy with high success rate")
    print("   - High confidence match: 0.95")
    print("   → Selects: ['calculator']")

    print("\n   For request: \"search for AI research papers\"")
    print("   AI reasoning:")
    print("   - Query contains 'search' → information retrieval")
    print("   - 'search' agent has 'search' and 'retrieval' capabilities")
    print("   - 'search' agent description mentions document search")
    print("   - High confidence match: 0.92")
    print("   → Selects: ['search']")

    await registry.cleanup_all()

    print("\n" + "=" * 70)


async def main():
    """Run all demonstrations."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 10 + "Agent Orchestrator: Registry & Selection Demo" + " " * 12 + "║")
    print("╚" + "═" * 68 + "╝")

    try:
        # Demonstrate registry
        await demonstrate_registry()

        # Demonstrate rule-based selection
        await demonstrate_agent_selection()

        # Demonstrate AI context
        await demonstrate_ai_context()

        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print("""
✅ Agent Registry: Stores all agent characteristics
   - Name, capabilities, metadata, health status
   - Indexed by capability for O(1) lookup
   - Tracks performance metrics

✅ Rule-Based Selection: Fast pattern matching
   - Matches input patterns against predefined rules
   - Deterministic and efficient
   - High confidence for common patterns

✅ AI-Based Selection: Intelligent reasoning
   - Analyzes all agent characteristics
   - Context-aware decision making
   - Handles complex, multi-step requests

✅ Hybrid Approach: Best of both worlds
   - Rules first (fast)
   - AI fallback (intelligent)
   - Resilient with fallback chain

The orchestrator acts as a supervisor that intelligently selects
the best agent(s) for each request based on stored characteristics!
        """)
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
