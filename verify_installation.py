#!/usr/bin/env python3
"""
Installation verification script for Agent Orchestrator.

Run this script after installation to verify everything is set up correctly.
"""

import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def check_python_version():
    """Check Python version."""
    print("=" * 60)
    print("Checking Python version...")
    print("=" * 60)

    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")

    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print("❌ Python 3.11 or higher required")
        return False

    print("✓ Python version OK")
    return True


def check_dependencies():
    """Check required dependencies."""
    print("\n" + "=" * 60)
    print("Checking dependencies...")
    print("=" * 60)

    required = [
        "fastmcp",
        "anthropic",
        "pydantic",
        "pydantic_settings",
        "jsonschema",
        "yaml",
        "tenacity",
        "aiohttp",
        "dotenv",
    ]

    missing = []

    for module in required:
        try:
            __import__(module)
            print(f"✓ {module}")
        except ImportError:
            print(f"❌ {module} - MISSING")
            missing.append(module)

    if missing:
        print(f"\n❌ Missing dependencies: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False

    print("\n✓ All dependencies installed")
    return True


def check_package_import():
    """Check if agent_orchestrator package can be imported."""
    print("\n" + "=" * 60)
    print("Checking package import...")
    print("=" * 60)

    try:
        from agent_orchestrator import Orchestrator
        print("✓ agent_orchestrator package imported successfully")
        print(f"✓ Orchestrator class available")
        return True
    except ImportError as e:
        print(f"❌ Failed to import agent_orchestrator: {e}")
        print("Run: pip install -e .")
        return False


def check_sample_agents():
    """Check if sample agents work."""
    print("\n" + "=" * 60)
    print("Checking sample agents...")
    print("=" * 60)

    try:
        from examples.sample_calculator import calculate

        result = calculate("add", [2, 3])
        if result["result"] == 5:
            print("✓ Calculator agent works")
        else:
            print(f"❌ Calculator returned unexpected result: {result}")
            return False
    except Exception as e:
        print(f"❌ Calculator agent failed: {e}")
        return False

    try:
        import asyncio
        from examples.sample_search import search_documents

        async def test_search():
            result = await search_documents("test")
            return result

        result = asyncio.run(test_search())
        if "query" in result and "results" in result:
            print("✓ Search agent works")
        else:
            print(f"❌ Search agent returned unexpected result: {result}")
            return False
    except Exception as e:
        print(f"❌ Search agent failed: {e}")
        return False

    print("\n✓ Sample agents working")
    return True


def check_configuration():
    """Check if configuration files load correctly."""
    print("\n" + "=" * 60)
    print("Checking configuration...")
    print("=" * 60)

    try:
        from agent_orchestrator.config import load_orchestrator_config

        config = load_orchestrator_config("config/orchestrator.yaml")
        print(f"✓ Orchestrator config loaded: {config.name}")
        print(f"  - Reasoning mode: {config.reasoning_mode}")
        print(f"  - Max parallel agents: {config.max_parallel_agents}")
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return False

    try:
        from agent_orchestrator.config import load_agents_config

        agents = load_agents_config("config/agents.yaml")
        print(f"✓ Agents config loaded: {len(agents.agents)} agents")
    except Exception as e:
        print(f"❌ Failed to load agents config: {e}")
        return False

    try:
        from agent_orchestrator.config import load_rules_config

        rules = load_rules_config("config/rules.yaml")
        print(f"✓ Rules config loaded: {len(rules.rules)} rules")
    except Exception as e:
        print(f"❌ Failed to load rules config: {e}")
        return False

    print("\n✓ Configuration files valid")
    return True


def check_api_key():
    """Check if API key is set."""
    print("\n" + "=" * 60)
    print("Checking API key...")
    print("=" * 60)

    import os

    api_key = os.getenv("ANTHROPIC_API_KEY")

    if api_key:
        print(f"✓ ANTHROPIC_API_KEY is set ({len(api_key)} characters)")
    else:
        print("⚠️  ANTHROPIC_API_KEY not set")
        print("   AI reasoning will not be available")
        print("   Set in .env file or export ANTHROPIC_API_KEY=your_key")

    return True  # Not critical, just a warning


def main():
    """Run all verification checks."""
    print("\n" + "=" * 60)
    print("Agent Orchestrator - Installation Verification")
    print("=" * 60)

    checks = [
        ("Python version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Package import", check_package_import),
        ("Sample agents", check_sample_agents),
        ("Configuration", check_configuration),
        ("API key", check_api_key),
    ]

    results = []

    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Unexpected error in {name}: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)

    all_passed = True
    for name, result in results:
        status = "✓" if result else "❌"
        print(f"{status} {name}")
        if not result and name != "API key":  # API key is optional
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 Installation verified successfully!")
        print("\nNext steps:")
        print("  1. python3 example_usage.py - Run examples")
        print("  2. pytest - Run tests")
        print("  3. See README.md for full documentation")
        return 0
    else:
        print("\n❌ Some checks failed. Please fix the issues above.")
        print("\nFor help, see INSTALLATION.md")
        return 1


if __name__ == "__main__":
    sys.exit(main())
