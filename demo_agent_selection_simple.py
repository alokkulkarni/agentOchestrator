#!/usr/bin/env python3
"""
Simple Demonstration: Agent Registry & Selection Concepts

This demonstrates the core concepts without requiring full dependencies.
"""


class SimpleAgent:
    """Simplified agent for demonstration."""

    def __init__(self, name, capabilities, description):
        self.name = name
        self.capabilities = capabilities
        self.description = description
        self.call_count = 0
        self.success_count = 0

    def __repr__(self):
        return f"Agent({self.name})"


class SimpleRegistry:
    """Simplified registry for demonstration."""

    def __init__(self):
        self._agents = {}
        self._capability_index = {}

    def register(self, agent):
        """Register an agent."""
        self._agents[agent.name] = agent

        # Index by capabilities
        for cap in agent.capabilities:
            cap_lower = cap.lower()
            if cap_lower not in self._capability_index:
                self._capability_index[cap_lower] = []
            self._capability_index[cap_lower].append(agent.name)

    def get_by_capability(self, capability):
        """Find agents by capability."""
        cap_lower = capability.lower()
        agent_names = self._capability_index.get(cap_lower, [])
        return [self._agents[name] for name in agent_names]

    def get_all(self):
        """Get all agents."""
        return list(self._agents.values())

    def count(self):
        """Count agents."""
        return len(self._agents)


def demonstrate():
    """Run demonstration."""
    print("\n" + "=" * 70)
    print("AGENT REGISTRY & SELECTION DEMONSTRATION")
    print("=" * 70)

    # Create registry
    registry = SimpleRegistry()

    print("\n1. CREATING AGENT REGISTRY")
    print(f"   Empty registry created: {registry.count()} agents")

    # Create agents
    calculator = SimpleAgent(
        name="calculator",
        capabilities=["math", "calculation", "arithmetic"],
        description="Safe mathematical calculator with input validation"
    )

    search = SimpleAgent(
        name="search",
        capabilities=["search", "retrieval", "query"],
        description="Document search with safe search enabled"
    )

    data_processor = SimpleAgent(
        name="data_processor",
        capabilities=["data", "transform", "json"],
        description="Data processing and transformation"
    )

    admin = SimpleAgent(
        name="admin_agent",
        capabilities=["admin", "system", "monitoring"],
        description="Administrative operations with approval requirements"
    )

    weather = SimpleAgent(
        name="weather",
        capabilities=["weather", "forecast", "climate"],
        description="Weather information via external API"
    )

    print("\n2. REGISTERING AGENTS WITH CHARACTERISTICS")
    print()

    for agent in [calculator, search, data_processor, admin, weather]:
        registry.register(agent)
        print(f"   ✅ {agent.name}")
        print(f"      Capabilities: {', '.join(agent.capabilities)}")
        print(f"      Description: {agent.description}")
        print()

    print(f"   Total registered: {registry.count()} agents")

    # Show capability index
    print("\n3. CAPABILITY INDEX (for fast lookup)")
    print()
    capability_index = {}
    for agent in registry.get_all():
        for cap in agent.capabilities:
            if cap not in capability_index:
                capability_index[cap] = []
            capability_index[cap].append(agent.name)

    for cap, agents in sorted(capability_index.items()):
        print(f"   '{cap}' → {agents}")

    # Demonstrate lookups
    print("\n4. FINDING AGENTS BY CAPABILITY")
    print()

    queries = [
        ("math", "Who can do math?"),
        ("search", "Who can search?"),
        ("data", "Who can process data?"),
        ("admin", "Who can do admin tasks?"),
        ("weather", "Who can get weather?"),
    ]

    for capability, question in queries:
        agents = registry.get_by_capability(capability)
        print(f"   Q: {question}")
        if agents:
            for agent in agents:
                print(f"      ✅ {agent.name}")
        else:
            print(f"      ❌ No agents found")
        print()

    # Demonstrate selection logic
    print("\n5. INTELLIGENT AGENT SELECTION")
    print()

    test_requests = [
        ("calculate 15 + 27", ["math", "calculation"], "calculator"),
        ("search for python tutorials", ["search", "query"], "search"),
        ("process user data", ["data", "transform"], "data_processor"),
        ("get system status", ["admin", "system"], "admin_agent"),
        ("what's the weather in Tokyo?", ["weather"], "weather"),
    ]

    for query, keywords, expected_agent in test_requests:
        print(f"   Request: \"{query}\"")

        # Simulate rule-based matching
        print(f"   Keywords detected: {', '.join(keywords)}")

        # Find matching agents
        matching_agents = set()
        for keyword in keywords:
            agents = registry.get_by_capability(keyword)
            matching_agents.update(agent.name for agent in agents)

        if matching_agents:
            selected = list(matching_agents)[0]  # Pick first match
            confidence = 0.9 if len(matching_agents) == 1 else 0.7
            print(f"   ✅ Selected: {selected}")
            print(f"   Confidence: {confidence:.2f}")
            print(f"   Method: {'rule' if confidence > 0.8 else 'hybrid'}")
        else:
            print(f"   ❌ No match - would use AI reasoning")

        print()

    # Show all available agents
    print("\n6. ALL AVAILABLE AGENTS IN REGISTRY")
    print()
    all_agents = registry.get_all()
    print(f"   Total: {len(all_agents)} agents\n")

    for agent in all_agents:
        print(f"   • {agent.name}")
        print(f"     Capabilities: {', '.join(agent.capabilities)}")
        print(f"     Description: {agent.description}")
        print()

    print("=" * 70)
    print("KEY TAKEAWAYS")
    print("=" * 70)
    print("""
✅ REGISTRY: Central storage for all agents
   - Stores agent name, capabilities, metadata
   - Indexes by capability for O(1) lookup
   - Easy to query and discover agents

✅ CAPABILITIES: Define what each agent can do
   - Multiple agents can have same capability
   - Used for matching requests to agents
   - Hierarchical (e.g., "math" → "calculation")

✅ SELECTION PROCESS:
   1. Analyze user request
   2. Extract keywords/requirements
   3. Match against agent capabilities
   4. Select agent(s) with highest confidence
   5. Execute selected agent(s)

✅ REASONING MODES:
   - Rule-based: Fast pattern matching (common requests)
   - AI-based: Intelligent analysis (complex requests)
   - Hybrid: Rule-first, AI-fallback (best of both)

The orchestrator acts as a SUPERVISOR that:
- Knows all available agents and their capabilities
- Intelligently routes requests to the right agent
- Tracks performance and health
- Provides fallback mechanisms
    """)
    print("=" * 70 + "\n")


if __name__ == "__main__":
    demonstrate()
