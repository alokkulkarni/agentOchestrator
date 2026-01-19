#!/usr/bin/env python3
"""
Quick demonstration of gateway fallback in action.

This script shows what happens when a provider fails.
"""

import asyncio
import aiohttp


async def demonstrate_fallback():
    """Demonstrate fallback with a real request."""
    print("\n" + "="*70)
    print("Gateway Fallback Demonstration")
    print("="*70)

    gateway_url = "http://localhost:8000"

    # Make a request requesting Anthropic
    request_data = {
        "messages": [
            {
                "role": "user",
                "content": "What is 100 + 200? Just give the number.",
            }
        ],
        "provider": "anthropic",  # Specifically request Anthropic
        "max_tokens": 50,
        "temperature": 0.0,
    }

    print(f"\n📤 Sending request to gateway...")
    print(f"   Requested provider: anthropic")
    print(f"   Gateway URL: {gateway_url}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{gateway_url}/v1/generate",
                json=request_data
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    print(f"\n✅ Response received successfully!")
                    print(f"   Provider used: {data['provider']}")
                    print(f"   Model: {data['model']}")
                    print(f"   Content: {data['content']}")
                    print(f"   Latency: {data['latency_ms']}ms")
                    print(f"   Tokens used: {data['usage']['total_tokens']}")

                    # Check if fallback occurred
                    if "bedrock" in data['provider'].lower():
                        print(f"\n🔄 FALLBACK DETECTED!")
                        print(f"   You requested: anthropic")
                        print(f"   Gateway used: {data['provider']}")
                        print(f"   This means Anthropic failed and Bedrock succeeded")
                        print(f"   ✅ Request completed successfully via fallback!")
                    else:
                        print(f"\n✅ No fallback needed - primary provider worked")

                else:
                    print(f"\n❌ Request failed with status {response.status}")
                    error = await response.text()
                    print(f"   Error: {error[:200]}")

        except Exception as e:
            print(f"\n❌ Error: {e}")

    print(f"\n{'='*70}")
    print("Check Gateway Logs")
    print(f"{'='*70}")
    print("\nTo see fallback logs in real-time:")
    print("  tail -f model_gateway/gateway.log | grep -E '⚠️|🔄'")
    print("\nLook for these log patterns:")
    print("  ⚠️  Provider 'X' failed - Warning about failure")
    print("  🔄 FALLBACK SUCCESS - Success with alternative provider")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(demonstrate_fallback())
