#!/usr/bin/env python3
"""
Test script for Model Gateway.

Tests both Anthropic and Bedrock providers through the gateway.
"""

import asyncio
import os
import sys

import aiohttp


async def test_gateway_health(gateway_url: str):
    """Test gateway health endpoint."""
    print(f"\n{'='*70}")
    print("Testing Gateway Health")
    print(f"{'='*70}")

    url = f"{gateway_url}/health"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Gateway Status: {data['status']}")
                    print(f"\nProvider Health:")
                    for name, health in data["providers"].items():
                        status_icon = "✅" if health["status"] == "healthy" else "❌"
                        print(f"  {status_icon} {name}: {health['status']}")
                        if "latency_ms" in health:
                            print(f"     Latency: {health['latency_ms']}ms")
                        if "error" in health and health["error"]:
                            print(f"     Error: {health['error']}")
                    return True
                else:
                    print(f"❌ Health check failed (status {response.status})")
                    return False
        except Exception as e:
            print(f"❌ Error connecting to gateway: {e}")
            return False


async def test_gateway_providers(gateway_url: str):
    """Test gateway providers endpoint."""
    print(f"\n{'='*70}")
    print("Testing Gateway Providers")
    print(f"{'='*70}")

    url = f"{gateway_url}/providers"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"\n✅ Available Providers:")
                    for name, info in data.items():
                        print(f"\n  Provider: {name}")
                        if "models" in info:
                            print(f"  Models: {len(info['models'])} available")
                            print(f"  Default: {info.get('default_model', 'N/A')}")
                        if "error" in info:
                            print(f"  ❌ Error: {info['error']}")
                    return True
                else:
                    print(f"❌ Providers check failed (status {response.status})")
                    return False
        except Exception as e:
            print(f"❌ Error getting providers: {e}")
            return False


async def test_gateway_generate(
    gateway_url: str,
    provider: str,
    model: str = None,
):
    """Test gateway generate endpoint."""
    print(f"\n{'='*70}")
    print(f"Testing Gateway Generate - Provider: {provider}")
    print(f"{'='*70}")

    url = f"{gateway_url}/v1/generate"

    request_data = {
        "messages": [
            {
                "role": "user",
                "content": "What is 25 + 75? Respond with just the number.",
            }
        ],
        "provider": provider,
        "max_tokens": 100,
        "temperature": 0.0,
    }

    if model:
        request_data["model"] = model

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Generation successful")
                    print(f"\nResponse:")
                    print(f"  Content: {data['content'][:100]}")
                    print(f"  Model: {data['model']}")
                    print(f"  Provider: {data['provider']}")
                    print(f"  Tokens: {data['usage']['total_tokens']}")
                    print(f"  Latency: {data['latency_ms']}ms")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Generation failed (status {response.status})")
                    print(f"  Error: {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Error generating: {e}")
            return False


async def main():
    """Main test function."""
    print("\n" + "="*70)
    print("Model Gateway Test Suite")
    print("="*70)

    # Check for required environment variables
    anthropic_key = os.getenv("GATEWAY_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

    if not anthropic_key:
        print("\n⚠️  Warning: GATEWAY_ANTHROPIC_API_KEY not set")
        print("   Set it in .env or environment to test Anthropic provider")

    # Gateway URL
    gateway_url = os.getenv("GATEWAY_URL", "http://localhost:8585")
    print(f"\nGateway URL: {gateway_url}")

    # Test 1: Health check
    health_ok = await test_gateway_health(gateway_url)
    await asyncio.sleep(1)

    # Test 2: List providers
    providers_ok = await test_gateway_providers(gateway_url)
    await asyncio.sleep(1)

    # Test 3: Generate with Anthropic (if available)
    anthropic_ok = False
    if anthropic_key:
        anthropic_ok = await test_gateway_generate(gateway_url, "anthropic")
        await asyncio.sleep(1)
    else:
        print(f"\n{'='*70}")
        print("⏭️  Skipping Anthropic generation test (no API key)")
        print(f"{'='*70}")

    # Test 4: Generate with Bedrock (if AWS credentials available)
    # Note: This will only work if AWS credentials are configured
    bedrock_ok = await test_gateway_generate(gateway_url, "bedrock")

    # Summary
    print(f"\n{'='*70}")
    print("Test Summary")
    print(f"{'='*70}")
    print(f"  Health Check: {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"  Providers List: {'✅ PASS' if providers_ok else '❌ FAIL'}")
    if anthropic_key:
        print(f"  Anthropic Generate: {'✅ PASS' if anthropic_ok else '❌ FAIL'}")
    else:
        print(f"  Anthropic Generate: ⏭️  SKIPPED")
    print(f"  Bedrock Generate: {'✅ PASS' if bedrock_ok else '❌ FAIL or SKIPPED'}")
    print(f"{'='*70}\n")

    # Return exit code
    if health_ok and providers_ok:
        if anthropic_key:
            return 0 if (health_ok and providers_ok and anthropic_ok) else 1
        else:
            return 0  # Pass if health and providers work
    return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
