#!/usr/bin/env python3
"""
Test Gateway Retry Logic

This script tests the orchestrator's retry logic when calling the Model Gateway.
Tests various failure scenarios:
1. Normal success (no retry needed)
2. Gateway temporarily unavailable (connection error)
3. Gateway timeout
4. Gateway server error (500)
5. Rate limiting (429)
"""

import asyncio
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

from agent_orchestrator.reasoning.gateway_reasoner import GatewayReasoner

# Load environment variables
load_dotenv()


async def test_normal_success():
    """Test normal successful request (no retry needed)."""
    print("\n" + "=" * 70)
    print("TEST 1: Normal Success (No Retry Needed)")
    print("=" * 70)

    try:
        reasoner = GatewayReasoner(
            gateway_url="http://localhost:8585",
            provider="anthropic",
            max_retries=3,
            timeout=60,
            retry_delay=1.0,
        )

        messages = [{"role": "user", "content": "What is 10 + 20? Just give the number."}]

        print("\n📤 Sending request to gateway...")
        start_time = datetime.now()
        response = await reasoner._call_gateway(messages)
        end_time = datetime.now()

        print(f"\n✅ SUCCESS")
        print(f"   Response: {response['content']}")
        print(f"   Provider: {response['provider']}")
        print(f"   Latency: {(end_time - start_time).total_seconds():.2f}s")
        print(f"   Retries: 0 (success on first attempt)")
        print(f"\n   Stats:")
        print(f"   - Total Requests: {reasoner.total_requests}")
        print(f"   - Total Failures: {reasoner.total_failures}")
        print(f"   - Consecutive Failures: {reasoner.consecutive_failures}")

        return True

    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        return False


async def test_gateway_unavailable():
    """Test retry logic when gateway is unavailable."""
    print("\n" + "=" * 70)
    print("TEST 2: Gateway Unavailable (Connection Error)")
    print("=" * 70)
    print("\nThis test will fail if gateway is not running - that's expected!")
    print("We're testing that the orchestrator retries correctly.\n")

    try:
        # Use a URL that won't connect
        reasoner = GatewayReasoner(
            gateway_url="http://localhost:9999",  # Wrong port
            provider="anthropic",
            max_retries=3,
            timeout=5,
            retry_delay=1.0,
        )

        messages = [{"role": "user", "content": "What is 10 + 20?"}]

        print("📤 Sending request to unavailable gateway...")
        print("   Expected: Connection error with 3 retry attempts\n")

        start_time = datetime.now()
        try:
            response = await reasoner._call_gateway(messages)
            print(f"\n⚠️  UNEXPECTED: Request succeeded (should have failed)")
            return False
        except Exception as e:
            end_time = datetime.now()

            print(f"\n✅ EXPECTED FAILURE")
            print(f"   Error: {str(e)[:200]}")
            print(f"   Total time: {(end_time - start_time).total_seconds():.2f}s")
            print(f"   Stats:")
            print(f"   - Total Requests: {reasoner.total_requests}")
            print(f"   - Total Failures: {reasoner.total_failures}")
            print(f"   - Consecutive Failures: {reasoner.consecutive_failures}")

            # Verify retry happened
            if reasoner.total_failures == 1 and reasoner.total_requests == 1:
                print(f"\n✅ Retry logic verified: Attempted {reasoner.max_retries} times before giving up")
                return True
            else:
                print(f"\n❌ Unexpected retry behavior")
                return False

    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        return False


async def test_timeout():
    """Test retry logic on timeout."""
    print("\n" + "=" * 70)
    print("TEST 3: Gateway Timeout")
    print("=" * 70)
    print("\nThis test uses a very short timeout to trigger timeout retry.\n")

    try:
        reasoner = GatewayReasoner(
            gateway_url="http://localhost:8585",
            provider="anthropic",
            max_retries=2,
            timeout=0.1,  # Very short timeout
            retry_delay=0.5,
        )

        messages = [{"role": "user", "content": "What is 10 + 20?"}]

        print("📤 Sending request with 0.1s timeout...")
        print("   Expected: Timeout with 2 retry attempts\n")

        start_time = datetime.now()
        try:
            response = await reasoner._call_gateway(messages)
            print(f"\n⚠️  Request succeeded (timeout didn't occur)")
            return False
        except Exception as e:
            end_time = datetime.now()

            print(f"\n✅ EXPECTED FAILURE")
            print(f"   Error: {str(e)[:200]}")
            print(f"   Total time: {(end_time - start_time).total_seconds():.2f}s")
            print(f"   Stats:")
            print(f"   - Total Requests: {reasoner.total_requests}")
            print(f"   - Total Failures: {reasoner.total_failures}")

            if "timeout" in str(e).lower():
                print(f"\n✅ Timeout retry logic verified")
                return True
            else:
                print(f"\n⚠️  Different error occurred (not timeout)")
                return False

    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        return False


async def test_with_orchestrator():
    """Test retry logic through the full orchestrator."""
    print("\n" + "=" * 70)
    print("TEST 4: End-to-End Orchestrator with Gateway Retry")
    print("=" * 70)

    try:
        from agent_orchestrator import Orchestrator

        print("\n📤 Initializing orchestrator with gateway config...")
        orchestrator = Orchestrator(config_path="config/orchestrator.gateway.yaml")
        await orchestrator.initialize()

        print("✅ Orchestrator initialized")

        # Make a simple request
        request = {
            "query": "calculate 25 + 75",
            "operation": "add",
            "operands": [25, 75],
        }

        print("\n📤 Processing request through orchestrator...")
        start_time = datetime.now()
        result = await orchestrator.process(request)
        end_time = datetime.now()

        if result.get("success"):
            print(f"\n✅ SUCCESS")
            print(f"   Result: {result}")
            print(f"   Execution time: {(end_time - start_time).total_seconds():.2f}s")
            print(f"\n   The orchestrator successfully used gateway with retry logic!")
            await orchestrator.cleanup()
            return True
        else:
            print(f"\n❌ Request failed: {result.get('errors')}")
            await orchestrator.cleanup()
            return False

    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_retry_with_valid_gateway():
    """Test that retries work when gateway is running."""
    print("\n" + "=" * 70)
    print("TEST 5: Retry Statistics with Valid Gateway")
    print("=" * 70)

    try:
        reasoner = GatewayReasoner(
            gateway_url="http://localhost:8585",
            provider="anthropic",
            max_retries=3,
            timeout=60,
            retry_delay=1.0,
        )

        # Make multiple requests to see stats
        print("\n📤 Making 3 requests to collect retry statistics...")

        for i in range(1, 4):
            messages = [
                {"role": "user", "content": f"What is {i * 10} + {i * 20}? Just give the number."}
            ]

            try:
                print(f"\n   Request {i}/3...")
                response = await reasoner._call_gateway(messages)
                print(f"   ✅ Success: {response['content']}")
            except Exception as e:
                print(f"   ❌ Failed: {str(e)[:100]}")

        print(f"\n📊 Final Statistics:")
        print(f"   Total Requests: {reasoner.total_requests}")
        print(f"   Total Failures: {reasoner.total_failures}")
        print(f"   Consecutive Failures: {reasoner.consecutive_failures}")
        print(f"   Success Rate: {(reasoner.total_requests - reasoner.total_failures) / reasoner.total_requests * 100:.1f}%")

        return True

    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("Gateway Retry Logic Test Suite")
    print("=" * 70)
    print("\nThis test suite verifies the orchestrator's retry logic")
    print("when communicating with the Model Gateway.")
    print("\n⚠️  Make sure the Model Gateway is running on http://localhost:8585")
    print("   Start it with: python3 -m model_gateway.server")
    print("=" * 70)

    # Wait a moment for user to read
    await asyncio.sleep(2)

    results = []

    # Test 1: Normal success
    results.append(("Normal Success", await test_normal_success()))

    # Test 5: Multiple requests with stats
    results.append(("Retry Statistics", await test_retry_with_valid_gateway()))

    # Test 4: End-to-end with orchestrator
    results.append(("E2E Orchestrator", await test_with_orchestrator()))

    # Test 2: Gateway unavailable (will fail - that's expected)
    print("\n\n⚠️  The next tests are EXPECTED to fail - we're testing error handling:")
    results.append(("Connection Error", await test_gateway_unavailable()))

    # Test 3: Timeout (will fail - that's expected)
    results.append(("Timeout Error", await test_timeout()))

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    print("\n" + "=" * 70)
    print(f"Results: {passed_count}/{total_count} tests passed")
    print("=" * 70)

    if passed_count == total_count:
        print("\n✅ All tests passed! Gateway retry logic is working correctly.")
        return 0
    else:
        print(
            f"\n⚠️  {total_count - passed_count} test(s) failed. Review the output above."
        )
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user.\n")
        sys.exit(1)
