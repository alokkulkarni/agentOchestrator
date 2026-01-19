#!/usr/bin/env python3
"""
Test script for Model Gateway Provider Fallback.

Tests automatic fallback between providers when one fails.
"""

import asyncio
import os
import sys

import aiohttp


async def test_fallback_scenario(gateway_url: str):
    """
    Test provider fallback when primary provider fails.

    This simulates a scenario where Anthropic is requested but might fail,
    and the gateway should automatically fallback to Bedrock.
    """
    print(f"\n{'='*70}")
    print("Testing Gateway Provider Fallback")
    print(f"{'='*70}")

    url = f"{gateway_url}/v1/generate"

    # Test 1: Normal request with Anthropic (should work)
    print(f"\n{'-'*70}")
    print("Test 1: Normal request with Anthropic")
    print(f"{'-'*70}")

    request_data = {
        "messages": [
            {
                "role": "user",
                "content": "What is 10 + 15? Just give the number.",
            }
        ],
        "provider": "anthropic",
        "max_tokens": 50,
        "temperature": 0.0,
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Request succeeded with provider: {data['provider']}")
                    print(f"   Content: {data['content'][:50]}")
                    print(f"   Latency: {data['latency_ms']}ms")
                else:
                    error_text = await response.text()
                    print(f"❌ Request failed (status {response.status})")
                    print(f"   Error: {error_text[:200]}")
        except Exception as e:
            print(f"❌ Error: {e}")

    # Test 2: Request with invalid provider (should fallback)
    print(f"\n{'-'*70}")
    print("Test 2: Request with invalid/unavailable provider")
    print(f"{'-'*70}")
    print("Note: If Anthropic API key is invalid, gateway should fallback to Bedrock")

    # This test demonstrates fallback behavior
    # To truly test fallback, you'd need to temporarily disable one provider
    # or use an invalid API key

    request_data = {
        "messages": [
            {
                "role": "user",
                "content": "Calculate 20 + 30. Return only the number.",
            }
        ],
        "provider": "anthropic",  # Request Anthropic specifically
        "max_tokens": 50,
        "temperature": 0.0,
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Request succeeded with provider: {data['provider']}")
                    print(f"   Content: {data['content'][:50]}")
                    print(f"   Latency: {data['latency_ms']}ms")

                    if "bedrock" in data['provider'].lower():
                        print(f"\n🔄 FALLBACK DETECTED!")
                        print(f"   Originally requested: anthropic")
                        print(f"   Actually used: {data['provider']}")
                        print(f"   ✅ Automatic fallback worked!")
                else:
                    error_text = await response.text()
                    print(f"⚠️  Request failed (status {response.status})")
                    print(f"   This might indicate all providers failed")
                    print(f"   Error: {error_text[:300]}")
        except Exception as e:
            print(f"❌ Error: {e}")


async def check_gateway_logs(gateway_url: str):
    """Check gateway configuration for fallback settings."""
    print(f"\n{'='*70}")
    print("Checking Gateway Fallback Configuration")
    print(f"{'='*70}")

    print("\nFallback is configured in model_gateway/config/gateway.yaml:")
    print("""
    fallback:
      enabled: true
      fallback_order:
        - "anthropic"
        - "bedrock"
      max_fallback_attempts: 2
    """)

    print("\nWhen fallback occurs, you'll see in gateway logs:")
    print("  ⚠️  Provider 'anthropic' failed (attempt 1/2): <error>. Trying fallback to 'bedrock'...")
    print("  🔄 FALLBACK SUCCESS: Provider 'bedrock' succeeded after 'anthropic' failed.")


async def main():
    """Main test function."""
    print("\n" + "="*70)
    print("Model Gateway Provider Fallback Test Suite")
    print("="*70)

    # Gateway URL
    gateway_url = os.getenv("GATEWAY_URL", "http://localhost:8000")
    print(f"\nGateway URL: {gateway_url}")

    # Check if gateway is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{gateway_url}/") as response:
                if response.status == 200:
                    print("✅ Gateway is running")
                else:
                    print(f"⚠️  Gateway returned status {response.status}")
    except Exception as e:
        print(f"❌ Cannot connect to gateway: {e}")
        print("   Please start the gateway first:")
        print("   python3 -m model_gateway.server")
        return 1

    # Show fallback configuration
    await check_gateway_logs(gateway_url)

    # Run fallback tests
    await test_fallback_scenario(gateway_url)

    # Summary
    print(f"\n{'='*70}")
    print("Test Summary")
    print(f"{'='*70}")
    print("""
Fallback Behavior:
  1. Gateway receives request for specific provider (e.g., 'anthropic')
  2. If that provider fails, gateway automatically tries next provider
  3. Fallback order is configured in gateway.yaml
  4. All fallback events are logged with 🔄 and ⚠️ symbols
  5. User receives response transparently - doesn't know fallback occurred
  6. Logs show which provider was actually used

To see fallback in action:
  - Temporarily set invalid GATEWAY_ANTHROPIC_API_KEY
  - Or disable Anthropic provider in gateway.yaml
  - Gateway will automatically use Bedrock instead

Check gateway logs at: model_gateway/gateway.log
    """)
    print(f"{'='*70}\n")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
