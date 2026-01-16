#!/usr/bin/env python3
"""
Performance testing suite for Agent Orchestrator.

Tests throughput (TPS/TPM) and latency percentiles (50th, 90th, 95th).
"""

import asyncio
import json
import statistics
import time
from dataclasses import dataclass
from typing import Dict, List, Any
from dotenv import load_dotenv

from agent_orchestrator import Orchestrator

# Load environment variables
load_dotenv()


@dataclass
class PerformanceMetrics:
    """Container for performance test results."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_duration: float
    response_times: List[float]

    @property
    def tps(self) -> float:
        """Transactions per second."""
        return self.successful_requests / self.total_duration if self.total_duration > 0 else 0

    @property
    def tpm(self) -> float:
        """Transactions per minute."""
        return self.tps * 60

    @property
    def p50(self) -> float:
        """50th percentile (median) response time in milliseconds."""
        if not self.response_times:
            return 0
        return statistics.median(self.response_times) * 1000

    @property
    def p90(self) -> float:
        """90th percentile response time in milliseconds."""
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * 0.90)
        return sorted_times[idx] * 1000

    @property
    def p95(self) -> float:
        """95th percentile response time in milliseconds."""
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[idx] * 1000

    @property
    def avg_response_time(self) -> float:
        """Average response time in milliseconds."""
        if not self.response_times:
            return 0
        return statistics.mean(self.response_times) * 1000

    @property
    def min_response_time(self) -> float:
        """Minimum response time in milliseconds."""
        if not self.response_times:
            return 0
        return min(self.response_times) * 1000

    @property
    def max_response_time(self) -> float:
        """Maximum response time in milliseconds."""
        if not self.response_times:
            return 0
        return max(self.response_times) * 1000


class PerformanceTester:
    """Performance testing orchestrator."""

    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator
        self.test_requests = self._generate_test_requests()

    def _generate_test_requests(self) -> List[Dict[str, Any]]:
        """Generate diverse test requests."""
        return [
            # Calculator requests (fast)
            {"query": "calculate 5 + 3", "operation": "add", "operands": [5, 3]},
            {"query": "calculate 10 * 20", "operation": "multiply", "operands": [10, 20]},
            {"query": "calculate 100 - 25", "operation": "subtract", "operands": [100, 25]},
            {"query": "calculate 50 / 5", "operation": "divide", "operands": [50, 5]},
            {"query": "calculate power 2^8", "operation": "power", "operands": [2, 8]},

            # Search requests (medium)
            {"query": "search for python", "max_results": 5},
            {"query": "search for machine learning", "max_results": 10},
            {"query": "search for API development", "max_results": 3},
            {"query": "search for async programming", "max_results": 7},

            # Data processing requests (slower)
            {
                "query": "process data",
                "operation": "transform",
                "data": [{"id": i, "value": i * 2} for i in range(10)]
            },
            {
                "query": "aggregate data",
                "operation": "aggregate",
                "data": [{"score": i * 10, "count": i} for i in range(20)],
                "filters": {"aggregations": ["count", "avg"]}
            },
        ]

    async def run_single_request(self, request: Dict[str, Any]) -> tuple[bool, float]:
        """
        Run a single request and measure response time.

        Returns:
            Tuple of (success, response_time_in_seconds)
        """
        start_time = time.time()
        try:
            result = await self.orchestrator.process(request)
            elapsed = time.time() - start_time
            return result.get('success', False), elapsed
        except Exception as e:
            elapsed = time.time() - start_time
            return False, elapsed

    async def run_concurrent_batch(self, batch_size: int, request_count: int) -> PerformanceMetrics:
        """
        Run requests in concurrent batches.

        Args:
            batch_size: Number of concurrent requests per batch
            request_count: Total number of requests to make

        Returns:
            Performance metrics
        """
        print(f"\nRunning {request_count} requests in batches of {batch_size}...")

        successful = 0
        failed = 0
        response_times = []

        start_time = time.time()

        # Run requests in batches
        for batch_num in range(0, request_count, batch_size):
            batch_tasks = []
            for i in range(batch_size):
                if batch_num + i >= request_count:
                    break

                # Round-robin through test requests
                request = self.test_requests[(batch_num + i) % len(self.test_requests)]
                batch_tasks.append(self.run_single_request(request))

            # Execute batch concurrently
            results = await asyncio.gather(*batch_tasks)

            # Collect results
            for success, response_time in results:
                if success:
                    successful += 1
                else:
                    failed += 1
                response_times.append(response_time)

            # Progress indicator
            completed = batch_num + len(batch_tasks)
            print(f"  Progress: {completed}/{request_count} requests completed", end='\r')

        total_duration = time.time() - start_time
        print(f"\n  Completed in {total_duration:.2f}s")

        return PerformanceMetrics(
            total_requests=request_count,
            successful_requests=successful,
            failed_requests=failed,
            total_duration=total_duration,
            response_times=response_times
        )

    async def run_sustained_load_test(self, duration_seconds: int, concurrency: int) -> PerformanceMetrics:
        """
        Run sustained load for a specific duration.

        Args:
            duration_seconds: How long to run the test
            concurrency: Number of concurrent requests

        Returns:
            Performance metrics
        """
        print(f"\nRunning sustained load test for {duration_seconds}s with concurrency={concurrency}...")

        successful = 0
        failed = 0
        response_times = []

        start_time = time.time()
        end_time = start_time + duration_seconds

        request_count = 0

        while time.time() < end_time:
            # Launch batch of concurrent requests
            batch_tasks = []
            for i in range(concurrency):
                request = self.test_requests[request_count % len(self.test_requests)]
                batch_tasks.append(self.run_single_request(request))
                request_count += 1

            # Execute batch
            results = await asyncio.gather(*batch_tasks)

            # Collect results
            for success, response_time in results:
                if success:
                    successful += 1
                else:
                    failed += 1
                response_times.append(response_time)

            # Progress indicator
            elapsed = time.time() - start_time
            print(f"  Elapsed: {elapsed:.1f}s | Requests: {request_count} | TPS: {successful/elapsed:.1f}", end='\r')

        total_duration = time.time() - start_time
        print(f"\n  Completed {request_count} requests in {total_duration:.2f}s")

        return PerformanceMetrics(
            total_requests=request_count,
            successful_requests=successful,
            failed_requests=failed,
            total_duration=total_duration,
            response_times=response_times
        )


def print_performance_report(test_name: str, metrics: PerformanceMetrics):
    """Print formatted performance report."""
    print("\n" + "=" * 70)
    print(f"PERFORMANCE TEST RESULTS: {test_name}")
    print("=" * 70)

    print("\n📊 THROUGHPUT METRICS")
    print("-" * 70)
    print(f"  Total Requests:       {metrics.total_requests:,}")
    print(f"  Successful:           {metrics.successful_requests:,} ({metrics.successful_requests/metrics.total_requests*100:.1f}%)")
    print(f"  Failed:               {metrics.failed_requests:,} ({metrics.failed_requests/metrics.total_requests*100:.1f}%)")
    print(f"  Total Duration:       {metrics.total_duration:.2f}s")
    print(f"  ")
    print(f"  ⚡ TPS (Trans/sec):    {metrics.tps:.2f} requests/second")
    print(f"  ⚡ TPM (Trans/min):    {metrics.tpm:.2f} requests/minute")

    print("\n⏱️  LATENCY METRICS (milliseconds)")
    print("-" * 70)
    print(f"  Minimum:              {metrics.min_response_time:.2f} ms")
    print(f"  Average:              {metrics.avg_response_time:.2f} ms")
    print(f"  Maximum:              {metrics.max_response_time:.2f} ms")
    print(f"  ")
    print(f"  📈 p50 (median):       {metrics.p50:.2f} ms")
    print(f"  📈 p90:                {metrics.p90:.2f} ms")
    print(f"  📈 p95:                {metrics.p95:.2f} ms")

    print("\n" + "=" * 70)


async def main():
    """Run comprehensive performance tests."""
    print("=" * 70)
    print("AGENT ORCHESTRATOR - PERFORMANCE TEST SUITE")
    print("=" * 70)

    # Initialize orchestrator
    print("\n🔧 Initializing orchestrator...")
    orchestrator = Orchestrator(config_path="config/orchestrator.yaml")
    await orchestrator.initialize()

    stats = orchestrator.get_stats()
    print(f"✅ Orchestrator initialized with {stats['agents']['total_agents']} agents")

    tester = PerformanceTester(orchestrator)

    try:
        # Test 1: Low concurrency baseline
        print("\n" + "=" * 70)
        print("TEST 1: BASELINE - Low Concurrency")
        print("=" * 70)
        metrics_1 = await tester.run_concurrent_batch(batch_size=5, request_count=100)
        print_performance_report("Baseline (5 concurrent, 100 requests)", metrics_1)

        # Test 2: Medium concurrency
        print("\n" + "=" * 70)
        print("TEST 2: MEDIUM LOAD - Medium Concurrency")
        print("=" * 70)
        metrics_2 = await tester.run_concurrent_batch(batch_size=10, request_count=200)
        print_performance_report("Medium Load (10 concurrent, 200 requests)", metrics_2)

        # Test 3: High concurrency
        print("\n" + "=" * 70)
        print("TEST 3: HIGH LOAD - High Concurrency")
        print("=" * 70)
        metrics_3 = await tester.run_concurrent_batch(batch_size=20, request_count=300)
        print_performance_report("High Load (20 concurrent, 300 requests)", metrics_3)

        # Test 4: Sustained load
        print("\n" + "=" * 70)
        print("TEST 4: SUSTAINED LOAD - 30 Second Test")
        print("=" * 70)
        metrics_4 = await tester.run_sustained_load_test(duration_seconds=30, concurrency=10)
        print_performance_report("Sustained Load (30s, 10 concurrent)", metrics_4)

        # Summary comparison
        print("\n" + "=" * 70)
        print("📊 PERFORMANCE SUMMARY - ALL TESTS")
        print("=" * 70)
        print(f"\n{'Test':<40} {'TPS':<12} {'TPM':<12} {'p50':<12} {'p90':<12} {'p95':<12}")
        print("-" * 70)
        print(f"{'Baseline (5 concurrent)':<40} {metrics_1.tps:<12.2f} {metrics_1.tpm:<12.2f} {metrics_1.p50:<12.2f} {metrics_1.p90:<12.2f} {metrics_1.p95:<12.2f}")
        print(f"{'Medium Load (10 concurrent)':<40} {metrics_2.tps:<12.2f} {metrics_2.tpm:<12.2f} {metrics_2.p50:<12.2f} {metrics_2.p90:<12.2f} {metrics_2.p95:<12.2f}")
        print(f"{'High Load (20 concurrent)':<40} {metrics_3.tps:<12.2f} {metrics_3.tpm:<12.2f} {metrics_3.p50:<12.2f} {metrics_3.p90:<12.2f} {metrics_3.p95:<12.2f}")
        print(f"{'Sustained Load (30s)':<40} {metrics_4.tps:<12.2f} {metrics_4.tpm:<12.2f} {metrics_4.p50:<12.2f} {metrics_4.p90:<12.2f} {metrics_4.p95:<12.2f}")
        print("=" * 70)

        print("\n✅ All performance tests completed successfully!")

    finally:
        # Cleanup
        print("\n🧹 Cleaning up orchestrator...")
        await orchestrator.cleanup()
        print("✅ Cleanup complete")


if __name__ == "__main__":
    asyncio.run(main())
